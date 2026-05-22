#!/usr/bin/env python3
import time
import threading
import unittest

from aureon.exchanges.capital_cfd_trader import CAPITAL_MIN_PROFIT_GBP, CFD_FLAGS, CapitalCFDTrader, CFDPosition, CFDShadowTrade


class ClientStub:
    def __init__(self, positions=None, close_result=None, fallback_result=None, open_result=None, confirm_result=None, accounts=None, resolved_market=None, market_snapshot=None):
        self._positions = list(positions or [])
        self._position_batches = None
        self._close_result = close_result if close_result is not None else {"success": True}
        self._fallback_result = fallback_result if fallback_result is not None else {"dealReference": "FALLBACK"}
        self._open_result = open_result if open_result is not None else {"dealReference": "REF1"}
        self._confirm_result = confirm_result if confirm_result is not None else {"dealId": "DOPEN", "level": 7282.6}
        self._accounts = list(accounts or [{"accountId": "A1", "balance": 54.34, "available": 54.34, "currency": "GBP"}])
        self._resolved_market = dict(resolved_market or {"epic": "CS.D.SILVER.CFD.IP", "symbol": "SILVER"})
        self._market_snapshot = dict(market_snapshot or {
            "instrument": {"epic": "CS.D.SILVER.CFD.IP", "name": "Silver"},
            "snapshot": {"marketStatus": "TRADEABLE", "bid": 7249.8, "offer": 7251.8},
            "dealingRules": {"minDealSize": {"value": 1}},
        })
        self.order_calls = []

    def get_positions(self):
        if self._position_batches is not None:
            if len(self._position_batches) > 1:
                return list(self._position_batches.pop(0))
            return list(self._position_batches[0])
        return list(self._positions)

    def get_accounts(self):
        return list(self._accounts)

    def get_account_balance(self):
        return {}

    def close_position(self, deal_id: str):
        return dict(self._close_result)

    def place_market_order(self, symbol: str, side: str, size: float, **kwargs):
        side = side.upper()
        if side in {"BUY", "SELL"}:
            self.order_calls.append((symbol, side, size, kwargs))
            return dict(self._open_result)
        return dict(self._fallback_result)

    def get_working_orders(self):
        return []

    def place_working_order(self, symbol: str, side: str, size: float, level: float, **kwargs):
        return {"dealReference": "WREF1", "submitted": True, "kwargs": kwargs}

    def update_position_limits(self, deal_id: str, **kwargs):
        return {"success": True, "deal_id": deal_id, "kwargs": kwargs}

    def confirm_order(self, deal_reference: str):
        return dict(self._confirm_result)

    def _resolve_market(self, symbol: str):
        return dict(self._resolved_market)

    def _get_market_snapshot(self, epic: str):
        return dict(self._market_snapshot)


class ThoughtBusStub:
    def __init__(self):
        self.published = []

    def publish(self, thought):
        self.published.append(thought)

    def recall(self, prefix: str, limit: int = 8):
        return []


class TestCapitalCFDSync(unittest.TestCase):
    def _build_trader(self, client):
        client.enabled = True
        client.init_error = ""
        trader = CapitalCFDTrader.__new__(CapitalCFDTrader)
        trader.client = client
        trader.positions = []
        trader.shadow_trades = []
        trader._prices = {}
        trader._prices_lock = threading.RLock()
        trader._prices_fetched_at = 0.0
        trader.stats = {
            "trades_opened": 0.0,
            "trades_closed": 0.0,
            "winning_trades": 0.0,
            "losing_trades": 0.0,
            "total_pnl_gbp": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
        }
        trader._latest_monitor_line = ""
        trader._latest_tick_line = ""
        trader._latest_order_error = ""
        trader._latest_order_trace_path = ""
        trader._capital_snapshot_cache = {}
        trader._capital_snapshot_error = ""
        trader._latest_target_snapshot = {}
        trader._latest_candidate_snapshot = []
        trader._swarm_snapshot = {"enabled": True, "leader": {}, "votes": [], "ranked": []}
        trader._hive_boosts = {}
        trader._rejection_cooldowns = {}
        trader._quad_gate_at = 0.0
        trader._quad_gate_ok = True
        trader._signal_brain = None
        trader._trade_profit_validator = None
        trader.unified_registry = None
        trader.unified_decision_engine = None
        trader.orchestrator = None
        trader.timeline_oracle = None
        trader.harmonic_fusion = None
        trader.thought_bus = None
        trader._registry_snapshot = {}
        trader._decision_snapshot = {}
        trader._orchestrator_snapshot = {}
        trader._timeline_snapshot = {}
        trader._fusion_snapshot = {}
        trader._lane_snapshot = {}
        trader._thought_bus_snapshot = {}
        trader._cognition_snapshot = {}
        trader._recent_closed_trades = []
        trader._shadow_validated_count = 0
        trader._shadow_failed_count = 0
        trader._dtp_trackers = {}
        trader._state_lock = threading.RLock()
        trader.penny_engine = None
        trader.start_time = time.time()
        trader.starting_equity_gbp = 0.0
        trader._last_live_event_at = 0.0
        trader._live_refresh_stop = threading.Event()
        trader._live_refresh_thread = None
        trader._last_deadman_kick_at = time.time()
        trader._last_scan = 0.0
        trader._last_monitor = 0.0
        trader._last_exchange_sync = 0.0
        trader._last_shadow_scan = 0.0
        trader._last_slot_fill_attempt = {"BUY": 0.0, "SELL": 0.0}
        trader._harmonic_wiring_audit = {}
        trader._harmonic_wiring_audit_at = time.time()
        trader._prev_change_pct = {}
        trader._last_wave_factors = {}
        trader._last_fast_profit_capture = {}
        trader._fast_profit_capture_by_deal = {}
        trader._capital_risk_envelope = {}
        trader._capital_trade_evidence = {}
        trader._capital_unified_waveform_check = {}
        trader._capital_no_loss_hold_queue = {}
        trader._capital_pending_order_envelope = {}
        trader._capital_last_working_order_submit = {}
        trader._capital_confidence_ratchet = {
            "schema_version": 1,
            "enabled": True,
            "last_live_candidate": {},
            "last_reset_reason": "",
        }
        trader._lambda_engine = None
        trader._probability_nexus = None
        trader._ensure_live_refresh = lambda: None
        trader._required_tp_pct_for_profit = lambda price, size: (CAPITAL_MIN_PROFIT_GBP / max(price * size, 0.0001)) * 100.0
        return trader

    def test_capital_preflight_reports_minimum_size_failure(self):
        trader = self._build_trader(ClientStub(market_snapshot={
            "instrument": {"epic": "CS.D.SILVER.CFD.IP", "name": "Silver"},
            "snapshot": {"marketStatus": "TRADEABLE", "bid": 7249.8, "offer": 7251.8},
            "dealingRules": {"minDealSize": {"value": 2}},
        }))

        preflight = trader._capital_preflight(
            "SILVER",
            1,
            {"price": 7250.8, "bid": 7249.8, "ask": 7251.8, "epic": "CS.D.SILVER.CFD.IP"},
            {"class": "commodity", "size": 1, "tp_pct": 0.75, "sl_pct": 0.45},
        )

        self.assertFalse(preflight["ok"])
        self.assertEqual(preflight["minimum_deal_size"], 2.0)
        self.assertIn("below Capital minimum", preflight["reason"])

    def test_capital_preflight_reports_market_status_and_balance(self):
        trader = self._build_trader(ClientStub(
            accounts=[{"accountId": "A1", "balance": 54.34, "available": 12.5, "currency": "GBP"}],
            market_snapshot={
                "instrument": {"epic": "CS.D.SILVER.CFD.IP", "name": "Silver"},
                "snapshot": {"marketStatus": "CLOSED", "bid": 7249.8, "offer": 7251.8},
                "dealingRules": {"minDealSize": {"value": 1}},
            },
        ))

        preflight = trader._capital_preflight(
            "SILVER",
            1,
            {"price": 7250.8, "bid": 7249.8, "ask": 7251.8, "epic": "CS.D.SILVER.CFD.IP"},
            {"class": "commodity", "size": 1, "tp_pct": 0.75, "sl_pct": 0.45},
        )

        self.assertFalse(preflight["ok"])
        self.assertEqual(preflight["available_balance"], 12.5)
        self.assertEqual(preflight["market_status"], "CLOSED")
        self.assertEqual(preflight["epic"], "CS.D.SILVER.CFD.IP")
        self.assertGreater(preflight["spread"], 0.0)
        self.assertIn("market not tradeable", preflight["reason"])

    def test_capital_preflight_reads_margin_from_deposit_bands_and_blocks_if_underfunded(self):
        trader = self._build_trader(ClientStub(
            accounts=[{"accountId": "A1", "balance": 20.0, "available": 20.0, "currency": "GBP"}],
            market_snapshot={
                "instrument": {
                    "epic": "EURGBP",
                    "name": "EUR/GBP",
                    "marginFactorUnit": "FACTOR",
                    "marginDepositBands": [{"margin": 0.05}],
                },
                "snapshot": {"marketStatus": "TRADEABLE", "bid": 100.0, "offer": 100.0},
                "dealingRules": {"minDealSize": {"value": 1}},
            },
        ))

        preflight = trader._capital_preflight(
            "EURGBP",
            5.0,
            {"price": 100.0, "bid": 100.0, "ask": 100.0, "epic": "EURGBP"},
            {"class": "forex", "size": 5.0, "tp_pct": 0.35, "sl_pct": 0.2},
        )

        self.assertFalse(preflight["ok"])
        self.assertAlmostEqual(preflight["margin_factor_pct"], 5.0)
        self.assertAlmostEqual(preflight["estimated_margin_required"], 25.0)
        self.assertIn("insufficient equity for estimated margin", preflight["reason"])

    def test_open_position_stops_on_preflight_failure(self):
        client = ClientStub(market_snapshot={
            "instrument": {"epic": "CS.D.SILVER.CFD.IP", "name": "Silver"},
            "snapshot": {"marketStatus": "TRADEABLE", "bid": 7249.8, "offer": 7251.8},
            "dealingRules": {"minDealSize": {"value": 2}},
        })
        trader = self._build_trader(client)

        result = trader._open_position(
            "SILVER",
            {"class": "commodity", "size": 1, "tp_pct": 0.75, "sl_pct": 0.45},
            {"price": 7282.6, "ask": 7282.6, "bid": 7281.6, "epic": "CS.D.SILVER.CFD.IP"},
        )

        self.assertIsNone(result)
        self.assertIn("preflight failed", trader._latest_order_error)
        self.assertEqual(client.order_calls, [])

    def test_sized_cfg_from_preflight_raises_to_capital_minimum_when_affordable(self):
        trader = self._build_trader(ClientStub())

        adjusted = trader._sized_cfg_from_preflight(
            {"class": "commodity", "size": 1, "tp_pct": 0.75, "sl_pct": 0.45},
            {"minimum_deal_size": 2, "price": 10, "available_balance": 54.34},
        )

        self.assertIsNotNone(adjusted)
        self.assertEqual(adjusted["size"], 2)

    def test_sized_cfg_from_preflight_refuses_unaffordable_minimum(self):
        trader = self._build_trader(ClientStub())

        adjusted = trader._sized_cfg_from_preflight(
            {"class": "commodity", "size": 1, "tp_pct": 0.75, "sl_pct": 0.45},
            {"minimum_deal_size": 10, "price": 100, "available_balance": 54.34},
        )

        self.assertIsNone(adjusted)

    def test_sized_cfg_from_preflight_uses_margin_not_notional_for_capital_minimum(self):
        trader = self._build_trader(ClientStub())

        adjusted = trader._sized_cfg_from_preflight(
            {"class": "commodity", "size": 1, "tp_pct": 0.75, "sl_pct": 0.45},
            {
                "minimum_deal_size": 2,
                "requested_size": 1,
                "price": 1000,
                "available_balance": 100,
                "margin_factor_pct": 5.0,
            },
        )

        self.assertIsNotNone(adjusted)
        self.assertEqual(adjusted["size"], 2)

    def test_apply_hft_analysis_zeroes_candidate_when_costs_fail(self):
        trader = self._build_trader(ClientStub())
        trader._capital_cost_profile = lambda symbol, size, price, tp_pct: {
            "notional": 100.0,
            "expected_gross_profit": 0.01,
            "round_trip_cost": 0.05,
            "expected_net_profit": -0.04,
        }

        scored = [{
            "symbol": "SILVER",
            "score": 2.0,
            "size": 1.0,
            "price": 100.0,
            "change_pct": 2.0,
            "spread_pct": 0.1,
            "tp_pct": 0.75,
        }]

        trader._apply_hft_analysis(scored)

        self.assertEqual(scored[0]["score"], 0.0)
        self.assertEqual(scored[0]["hft_reason"], "cost_gate")

    def test_apply_hft_analysis_uses_signal_brain_when_available(self):
        class BrainStub:
            def decide(self, symbol, base_score, features, population_scores):
                class Decision:
                    score = base_score * 3
                    coherence = 0.77
                return Decision()

        trader = self._build_trader(ClientStub())
        trader._signal_brain = BrainStub()
        trader._capital_cost_profile = lambda symbol, size, price, tp_pct: {
            "notional": 100.0,
            "expected_gross_profit": 2.0,
            "round_trip_cost": 0.2,
            "expected_net_profit": 1.8,
        }

        scored = [{
            "symbol": "SILVER",
            "score": 2.0,
            "size": 1.0,
            "price": 100.0,
            "change_pct": 2.0,
            "spread_pct": 0.1,
            "tp_pct": 0.75,
        }]

        trader._apply_hft_analysis(scored)

        self.assertEqual(scored[0]["score"], 6.0)
        self.assertEqual(scored[0]["brain_coherence"], 0.77)

    def test_status_lines_include_latest_monitor_line(self):
        trader = self._build_trader(ClientStub())
        trader._latest_monitor_line = "CAPITAL SLOT FILL EURUSD BUY deal=D1"

        lines = trader.status_lines()

        self.assertTrue(any("Monitor: CAPITAL SLOT FILL EURUSD BUY deal=D1" in line for line in lines))

    def test_get_capital_snapshot_reuses_last_good_snapshot_when_feed_goes_empty(self):
        client = ClientStub(accounts=[{"accountId": "A1", "balance": 129.07, "available": 129.07, "currency": "GBP"}])
        trader = self._build_trader(client)

        first = trader.get_capital_snapshot()
        client._accounts = []
        second = trader.get_capital_snapshot()

        self.assertEqual(first["equity_gbp"], 129.07)
        self.assertEqual(second["equity_gbp"], 129.07)
        self.assertEqual(second["free_gbp"], 129.07)
        self.assertEqual(second.get("stale", 0.0), 1.0)

    def test_status_lines_include_tick_and_stale_capital_feed(self):
        trader = self._build_trader(ClientStub())
        trader._latest_tick_line = "CAPITAL TICK sync=0.01s prices=0.02s"
        trader._capital_snapshot_cache = {
            "equity_gbp": 129.07,
            "free_gbp": 129.07,
            "used_gbp": 0.0,
            "budget_gbp": 90.35,
            "target_pct_equity": 0.01,
        }

        trader.client._accounts = []
        lines = trader.status_lines()

        self.assertTrue(any("Tick: CAPITAL TICK sync=0.01s prices=0.02s" in line for line in lines))
        self.assertTrue(any("CapitalFeed: stale_snapshot" in line for line in lines))

    def test_capital_cost_profile_uses_passed_quote_not_refetched_quote(self):
        trader = self._build_trader(ClientStub())
        trader._trade_profit_validator = object()
        trader._get_price = lambda symbol: {"bid": 1.0, "ask": 99.0}

        profile = trader._capital_cost_profile(
            "EURUSD",
            0.01,
            1.085,
            0.921658986175115,
            bid=1.08498,
            ask=1.08502,
        )

        self.assertAlmostEqual(profile["round_trip_cost"], 0.0000005, places=10)
        self.assertGreater(profile["expected_net_profit"], 0.00009)

    def test_capital_preflight_no_longer_produces_absurd_stock_costs_from_mismatched_refetch(self):
        client = ClientStub(
            accounts=[{"accountId": "A1", "balance": 129.07, "available": 129.07, "currency": "GBP"}],
            market_snapshot={
                "instrument": {"epic": "AAPL.EPIC", "name": "Apple"},
                "snapshot": {"marketStatus": "TRADEABLE", "bid": 199.96, "offer": 200.04},
                "dealingRules": {"minDealSize": {"value": 1}},
            },
        )
        trader = self._build_trader(client)
        trader._trade_profit_validator = object()
        trader._get_price = lambda symbol: {"bid": 150.0, "ask": 175.0}

        preflight = trader._capital_preflight(
            "AAPL",
            1.0,
            {"price": 200.0, "bid": 199.96, "ask": 200.04, "epic": "AAPL.EPIC"},
            {"class": "stock", "size": 1.0, "tp_pct": 0.9, "sl_pct": 0.55},
        )

        self.assertLess(preflight["round_trip_cost"], 0.2)
        self.assertGreater(preflight["expected_net_profit"], 1.6)
        self.assertTrue(preflight["ok"])

    def test_queue_background_shadows_runs_even_when_live_lanes_are_full(self):
        trader = self._build_trader(ClientStub())
        trader.positions = [
            CFDPosition("US100", "D1", "E1", "BUY", 1.0, 100.0, 101.0, 99.0, "indices"),
            CFDPosition("AUDUSD", "D2", "E2", "SELL", 0.01, 1.0, 0.99, 1.01, "currencies"),
        ]
        created = []
        trader._ranked_opportunities = lambda: [
            ("US500", {"direction": "SELL", "class": "index", "size": 1.0}, {"price": 5000.0, "bid": 4999.0, "ask": 5001.0}),
            ("EURUSD", {"direction": "BUY", "class": "forex", "size": 0.01}, {"price": 1.085, "bid": 1.0849, "ask": 1.0851}),
        ]
        trader._capital_preflight = lambda symbol, size, ticker, cfg: {
            "ok": True,
            "symbol": symbol,
            "price": ticker.get("price"),
            "bid": ticker.get("bid"),
            "ask": ticker.get("ask"),
        }
        trader._create_shadow = lambda symbol, cfg, ticker: created.append((symbol, cfg["direction"])) or object()

        queued = trader._queue_background_shadows()

        self.assertEqual(queued, 2)
        self.assertEqual(created, [("US500", "SELL"), ("EURUSD", "BUY")])

    def test_active_universe_can_focus_symbols(self):
        trader = self._build_trader(ClientStub())
        original = __import__("aureon.exchanges.capital_cfd_trader", fromlist=["CAPITAL_FOCUS_SYMBOLS"])
        old_focus = original.CAPITAL_FOCUS_SYMBOLS
        try:
            original.CAPITAL_FOCUS_SYMBOLS = ("GOLD",)
            active = trader._active_universe()
            self.assertEqual(set(active.keys()), {"GOLD"})
        finally:
            original.CAPITAL_FOCUS_SYMBOLS = old_focus

    def test_deadman_guard_holds_losing_positions_when_stale(self):
        """Deadman respects profit_only_closes: losing positions are held."""
        trader = self._build_trader(ClientStub())
        trader.positions = [
            CFDPosition("GOLD", "D1", "E1", "BUY", 0.1, 3000.0, 3020.0, 2980.0, "commodity"),
            CFDPosition("GOLD", "D2", "E2", "SELL", 0.1, 3000.0, 2980.0, 3020.0, "commodity"),
        ]
        closed = []
        trader._close_position = lambda pos, reason: closed.append((pos.deal_id, reason)) or {"deal_id": pos.deal_id}

        original = __import__("aureon.exchanges.capital_cfd_trader", fromlist=["CAPITAL_DEADMAN_ENABLED", "CAPITAL_DEADMAN_STALE_SECS", "CFD_FLAGS"])
        old_enabled = original.CAPITAL_DEADMAN_ENABLED
        old_stale = original.CAPITAL_DEADMAN_STALE_SECS
        try:
            original.CAPITAL_DEADMAN_ENABLED = True
            original.CAPITAL_DEADMAN_STALE_SECS = 5.0
            # With profit_only_closes=True (default), losing positions should be HELD
            original.CFD_FLAGS["profit_only_closes"] = True
            trader._last_deadman_kick_at = time.time() - 10.0
            trader._deadman_guard(time.time())
        finally:
            original.CAPITAL_DEADMAN_ENABLED = old_enabled
            original.CAPITAL_DEADMAN_STALE_SECS = old_stale

        # Positions at zero/negative PnL are held, not closed
        self.assertEqual(len(closed), 0)

    def test_deadman_guard_closes_profitable_positions_when_stale(self):
        """Deadman closes positions that are in profit."""
        trader = self._build_trader(ClientStub())
        # BUY at 3000, current_price=3010 → profitable
        pos_buy = CFDPosition("GOLD", "D1", "E1", "BUY", 0.1, 3000.0, 3020.0, 2980.0, "commodity")
        pos_buy.current_price = 3010.0
        # SELL at 3000, current_price=2990 → profitable
        pos_sell = CFDPosition("GOLD", "D2", "E2", "SELL", 0.1, 3000.0, 2980.0, 3020.0, "commodity")
        pos_sell.current_price = 2990.0
        trader.positions = [pos_buy, pos_sell]
        trader._disable_market_hours_guard = True
        closed = []
        trader._close_position = lambda pos, reason: closed.append((pos.deal_id, reason)) or {"deal_id": pos.deal_id}

        original = __import__("aureon.exchanges.capital_cfd_trader", fromlist=["CAPITAL_DEADMAN_ENABLED", "CAPITAL_DEADMAN_STALE_SECS", "CFD_FLAGS"])
        old_enabled = original.CAPITAL_DEADMAN_ENABLED
        old_stale = original.CAPITAL_DEADMAN_STALE_SECS
        try:
            original.CAPITAL_DEADMAN_ENABLED = True
            original.CAPITAL_DEADMAN_STALE_SECS = 5.0
            original.CFD_FLAGS["profit_only_closes"] = True
            trader._last_deadman_kick_at = time.time() - 10.0
            trader._deadman_guard(time.time())
        finally:
            original.CAPITAL_DEADMAN_ENABLED = old_enabled
            original.CAPITAL_DEADMAN_STALE_SECS = old_stale

        self.assertEqual(len(closed), 2)
        self.assertTrue(all("DEADMAN_STALE" in reason for _, reason in closed))

    def test_continuous_watch_symbols_includes_universe_positions_and_shadows(self):
        trader = self._build_trader(ClientStub())
        trader.positions = [
            CFDPosition("US100", "D1", "E1", "BUY", 1.0, 100.0, 101.0, 99.0, "indices"),
        ]
        trader.shadow_trades = [
            CFDShadowTrade("GOLD", "BUY", "commodity", 0.1, 3000.0, 0.75, 10.0),
        ]
        original = __import__("aureon.exchanges.capital_cfd_trader", fromlist=["CAPITAL_FOCUS_SYMBOLS"])
        old_focus = original.CAPITAL_FOCUS_SYMBOLS
        try:
            original.CAPITAL_FOCUS_SYMBOLS = ("GOLD",)
            watched = trader._continuous_watch_symbols()
        finally:
            original.CAPITAL_FOCUS_SYMBOLS = old_focus

        self.assertEqual(watched, ["GOLD", "US100"])

    def test_handle_live_price_events_triggers_actuation_on_meaningful_move(self):
        trader = self._build_trader(ClientStub())
        calls = []
        trader._quad_gate = lambda: 1.0
        trader._refresh_unified_intel_snapshot = lambda: calls.append("intel")
        trader._refresh_thought_bus_snapshot = lambda: calls.append("thought")
        trader._find_best_opportunity = lambda: calls.append("find")
        trader._queue_background_shadows = lambda: calls.append("queue") or 1
        trader._fill_live_monitoring_slots = lambda now: calls.append("fill") or True

        original = __import__("aureon.exchanges.capital_cfd_trader", fromlist=["CAPITAL_LIVE_EVENT_TRIGGER_PCT"])
        old_trigger = original.CAPITAL_LIVE_EVENT_TRIGGER_PCT
        try:
            original.CAPITAL_LIVE_EVENT_TRIGGER_PCT = 0.03
            trader._last_live_event_at = 0.0
            trader._handle_live_price_events(
                {"GOLD": {"price": 3000.0}},
                {"GOLD": {"price": 3001.2}},
            )
        finally:
            original.CAPITAL_LIVE_EVENT_TRIGGER_PCT = old_trigger

        self.assertEqual(calls, ["intel", "thought", "find", "queue", "fill"])

    def test_handle_live_price_events_force_triggers_without_price_move(self):
        trader = self._build_trader(ClientStub())
        calls = []
        trader._quad_gate = lambda: 1.0
        trader._refresh_unified_intel_snapshot = lambda: calls.append("intel")
        trader._refresh_thought_bus_snapshot = lambda: calls.append("thought")
        trader._find_best_opportunity = lambda: calls.append("find")
        trader._queue_background_shadows = lambda: calls.append("queue") or 1
        trader._fill_live_monitoring_slots = lambda now: calls.append("fill") or True

        trader._handle_live_price_events(
            {"GOLD": {"price": 3000.0}},
            {"GOLD": {"price": 3000.0}},
            force=True,
        )

        self.assertEqual(calls, ["intel", "thought", "find", "queue", "fill"])

    def test_self_confidence_boosts_score_when_recent_validation_is_strong(self):
        trader = self._build_trader(ClientStub())
        trader._shadow_validated_count = 5
        trader._shadow_failed_count = 0
        trader._capital_cost_profile = lambda symbol, size, price, tp_pct: {
            "notional": 100.0,
            "expected_gross_profit": 2.0,
            "round_trip_cost": 0.2,
            "expected_net_profit": 1.8,
        }
        scored = [{
            "symbol": "SILVER",
            "direction": "BUY",
            "score": 2.0,
            "size": 1.0,
            "price": 100.0,
            "change_pct": 2.0,
            "spread_pct": 0.1,
            "tp_pct": 0.75,
            "brain_coherence": 0.8,
        }]

        trader._apply_intelligence_overlays(scored)

        self.assertGreater(scored[0]["self_confidence"], 0.55)
        self.assertGreater(scored[0]["self_confidence_boost"], 1.0)
        self.assertGreater(scored[0]["score"], 2.0)

    def test_shadow_promotion_gate_shortens_wait_when_confidence_is_high(self):
        trader = self._build_trader(ClientStub())
        trader._shadow_validated_count = 4
        trader._shadow_failed_count = 0
        trader._latest_target_snapshot = {
            "symbol": "SILVER",
            "direction": "BUY",
            "timeline_confidence": 0.9,
            "fusion_global_coherence": 0.9,
        }
        trader._latest_candidate_snapshot = [{
            "symbol": "SILVER",
            "direction": "BUY",
            "brain_coherence": 0.9,
        }]
        trader._probability_validation_snapshot = lambda force=False: {
            "ok": True,
            "direction_accuracy": 0.9,
            "profit_factor": 1.5,
        }
        gate = trader._build_shadow_promotion_gate(
            CFDShadowTrade(
                symbol="SILVER",
                direction="BUY",
                asset_class="commodity",
                size=1,
                entry_price=100.0,
                target_move_pct=0.1,
                score=2.0,
            ),
            {"change_pct": 1.5},
        )

        self.assertTrue(gate["ok"])
        self.assertLess(gate["validation_window_secs"], trader.SHADOW_MIN_VALIDATE)

    def test_growth_metrics_capture_session_velocity_and_trend(self):
        trader = self._build_trader(ClientStub())
        trader.start_time = time.time() - 3600
        trader.starting_equity_gbp = 100.0
        trader.get_capital_snapshot = lambda: {
            "equity_gbp": 112.0,
            "free_gbp": 90.0,
            "used_gbp": 22.0,
            "budget_gbp": 50.0,
            "target_pct_equity": 0.01,
        }
        trader.stats.update({
            "trades_closed": 4.0,
            "winning_trades": 3.0,
            "losing_trades": 1.0,
            "total_pnl_gbp": 8.0,
        })
        trader._recent_closed_trades = [
            {"net_pnl": 1.0},
            {"net_pnl": 3.0},
            {"net_pnl": 6.0},
        ]

        metrics = trader._compute_growth_metrics()

        self.assertAlmostEqual(metrics["equity_growth_pct"], 12.0)
        self.assertGreater(metrics["pnl_per_hour_gbp"], 7.9)
        self.assertAlmostEqual(metrics["trades_per_hour"], 4.0, places=1)
        self.assertEqual(metrics["trend"], "accelerating")

    def test_capital_cost_profile_uses_live_spread_instead_of_generic_fee_profile(self):
        trader = self._build_trader(ClientStub())
        trader._trade_profit_validator = object()
        trader._prices = {
            "SILVER": {"bid": 99.9, "ask": 100.1, "price": 100.0}
        }

        costs = trader._capital_cost_profile("SILVER", 1.0, 100.0, 0.75)

        self.assertAlmostEqual(costs["expected_gross_profit"], 0.75, places=4)
        self.assertLess(costs["round_trip_cost"], 0.25)
        self.assertGreater(costs["expected_net_profit"], 0.5)

    def test_close_position_feeds_learning_back_into_brain(self):
        class BrainStub:
            def __init__(self):
                self.calls = []

            def learn_from_outcome(self, symbol, pnl, confidence=0.5):
                self.calls.append((symbol, pnl, confidence))
                return {"symbol_bias": 0.1, "reward": pnl}

            def learning_snapshot(self):
                return {"total_feedback": 1.0, "win_bias": 1.0}

        trader = self._build_trader(ClientStub(close_result={"success": True}))
        trader._signal_brain = BrainStub()
        trader._latest_candidate_snapshot = [{
            "symbol": "SILVER",
            "brain_coherence": 0.8,
            "self_confidence": 0.7,
        }]
        pos = CFDPosition(
            symbol="SILVER",
            deal_id="D5",
            epic="CS.D.SILVER.CFD.IP",
            direction="BUY",
            size=1,
            entry_price=100.0,
            tp_price=101.0,
            sl_price=99.0,
            asset_class="commodity",
            current_price=101.0,
        )

        record = trader._close_position(pos, "TP_HIT")

        self.assertIn("learning_update", record)
        self.assertEqual(trader._signal_brain.calls[0][0], "SILVER")
        self.assertGreater(trader._signal_brain.calls[0][1], 0.0)

    def test_close_position_publishes_learning_to_queen_systems(self):
        class BrainStub:
            def learn_from_outcome(self, symbol, pnl, confidence=0.5):
                return {"symbol_bias": 0.12, "reward": pnl}

        trader = self._build_trader(ClientStub(close_result={"success": True}))
        trader._signal_brain = BrainStub()
        trader.thought_bus = ThoughtBusStub()
        from aureon.core.aureon_thought_bus import Thought
        import aureon.exchanges.capital_cfd_trader as capital_cfd_trader_module
        capital_cfd_trader_module.Thought = Thought
        pos = CFDPosition(
            symbol="SILVER",
            deal_id="D6",
            epic="CS.D.SILVER.CFD.IP",
            direction="BUY",
            size=1,
            entry_price=100.0,
            tp_price=101.0,
            sl_price=99.0,
            asset_class="commodity",
            current_price=101.0,
        )

        trader._close_position(pos, "TP_HIT")

        topics = [thought.topic for thought in trader.thought_bus.published]
        self.assertIn("brain.learning", topics)
        self.assertIn("queen.learning", topics)

    def test_score_symbol_maps_negative_momentum_to_sell(self):
        trader = self._build_trader(ClientStub())

        score, direction = trader._score_symbol(
            "SILVER",
            {"class": "commodity", "size": 1, "tp_pct": 0.75, "sl_pct": 0.45, "max_spread_pct": 0.15, "momentum_threshold": 0.20},
            {"price": 100.0, "bid": 99.99, "ask": 100.01, "change_pct": -2.5, "high": 105.0, "low": 95.0},
        )

        self.assertGreater(score, 0.0)
        self.assertEqual(direction, "SELL")

    def test_effective_tp_pct_keeps_configured_target_without_penny_engine(self):
        old_flag = CFD_FLAGS["penny_take_profit"]
        CFD_FLAGS["penny_take_profit"] = True
        try:
            trader = self._build_trader(ClientStub())
            effective_tp_pct = trader._effective_tp_pct(100.0, 1.0, {"tp_pct": 0.75})
            self.assertAlmostEqual(effective_tp_pct, 0.75)
        finally:
            CFD_FLAGS["penny_take_profit"] = old_flag

    def test_effective_tp_pct_uses_penny_engine_threshold_when_available(self):
        class EngineStub:
            @staticmethod
            def get_threshold(exchange, entry_value):
                return type("Threshold", (), {"win_pct": 0.49})()

        old_flag = CFD_FLAGS["penny_take_profit"]
        CFD_FLAGS["penny_take_profit"] = True
        try:
            trader = self._build_trader(ClientStub())
            trader.penny_engine = EngineStub()
            effective_tp_pct = trader._effective_tp_pct(100.0, 1.0, {"tp_pct": 0.75})
            self.assertAlmostEqual(effective_tp_pct, 0.49)
        finally:
            CFD_FLAGS["penny_take_profit"] = old_flag

    def test_tick_skips_failed_top_candidate_and_moves_to_next(self):
        trader = self._build_trader(ClientStub())
        trader._last_scan = 0.0
        trader._last_monitor = time.time()
        trader._sync_positions_from_exchange = lambda force=False: None
        trader._refresh_prices = lambda: None
        trader._monitor_positions = lambda: []
        trader._quad_gate = lambda: 1.0
        trader.status_lines = lambda: []
        trader._queue_background_shadows = lambda: 0
        trader._find_best_opportunity = lambda: ("SILVER", {"class": "commodity", "size": 1}, {"price": 10, "ask": 10, "bid": 9.9})
        trader._ranked_opportunities = lambda: [
            ("SILVER", {"class": "commodity", "size": 1}, {"price": 10, "ask": 10, "bid": 9.9}),
            ("GOLD", {"class": "commodity", "size": 1}, {"price": 10, "ask": 10, "bid": 9.9}),
        ]
        trader._capital_preflight = lambda symbol, size, ticker, cfg=None: {
            "ok": symbol == "GOLD",
            "reason": "rejected by preflight" if symbol == "SILVER" else "ok",
            "market_status": "TRADEABLE",
            "minimum_deal_size": 1.0,
            "available_balance": 54.34,
        }
        opened = []
        trader._create_shadow = lambda symbol, cfg, ticker: opened.append(symbol) or object()

        original = __import__("aureon.exchanges.capital_cfd_trader", fromlist=["CAPITAL_FORCE_SLOT_FILL"])
        old_force_slot_fill = original.CAPITAL_FORCE_SLOT_FILL
        try:
            original.CAPITAL_FORCE_SLOT_FILL = False
            trader.tick()
        finally:
            original.CAPITAL_FORCE_SLOT_FILL = old_force_slot_fill

        self.assertEqual(opened, ["GOLD"])
        self.assertIn("rejected by preflight", trader._latest_order_error)

    def test_tick_rescans_immediately_after_close_without_waiting_for_scan_interval(self):
        trader = self._build_trader(ClientStub())
        trader.positions = []
        trader._last_scan = time.time()
        trader._last_monitor = 0.0
        trader._sync_positions_from_exchange = lambda force=False: None
        trader._refresh_prices = lambda: None
        trader._update_position_prices = lambda: None
        trader._monitor_positions = lambda: [{"symbol": "SILVER", "pnl_gbp": 0.12}]
        trader._quad_gate = lambda: 1.0
        trader.status_lines = lambda: []
        trader._find_best_opportunity = lambda: ("GOLD", {"class": "commodity", "size": 1}, {"price": 10, "ask": 10, "bid": 9.9})
        trader._ranked_opportunities = lambda: [
            ("GOLD", {"class": "commodity", "size": 1}, {"price": 10, "ask": 10, "bid": 9.9}),
        ]
        trader._capital_preflight = lambda symbol, size, ticker, cfg=None: {
            "ok": True,
            "reason": "ok",
            "market_status": "TRADEABLE",
            "minimum_deal_size": 1.0,
            "available_balance": 54.34,
        }
        opened = []
        trader._create_shadow = lambda symbol, cfg, ticker: opened.append(symbol) or object()

        closed = trader.tick()

        self.assertEqual(len(closed), 1)
        self.assertEqual(opened, ["GOLD"])

    def test_ranked_opportunities_allows_extra_direction_when_dynamic_expansion_enabled(self):
        trader = self._build_trader(ClientStub())
        trader.positions = [
            CFDPosition(
                symbol="SILVER",
                deal_id="DBUY",
                epic="CS.D.SILVER.CFD.IP",
                direction="BUY",
                size=1,
                entry_price=7282.6,
                tp_price=7337.2,
                sl_price=7249.8,
                asset_class="commodity",
                current_price=7282.6,
            )
        ]
        trader._latest_candidate_snapshot = [
            {"symbol": "SILVER", "direction": "BUY", "score": 3.0},
            {"symbol": "GOLD", "direction": "BUY", "score": 2.0},
            {"symbol": "SILVER", "direction": "SELL", "score": 1.8},
        ]
        trader._get_price = lambda symbol: {"price": 10, "bid": 9.9, "ask": 10.1}

        ranked = trader._ranked_opportunities()

        self.assertEqual([(sym, cfg["direction"]) for sym, cfg, _ in ranked], [("GOLD", "BUY"), ("SILVER", "SELL")])

    def test_tick_can_open_one_buy_and_one_sell_in_same_cycle(self):
        trader = self._build_trader(ClientStub())
        trader.positions = []
        trader._last_scan = 0.0
        trader._last_monitor = time.time()
        trader._sync_positions_from_exchange = lambda force=False: None
        trader._refresh_prices = lambda: None
        trader._monitor_positions = lambda: []
        trader._quad_gate = lambda: 1.0
        trader.status_lines = lambda: []
        trader._queue_background_shadows = lambda: 0
        trader._find_best_opportunity = lambda: ("SILVER", {"class": "commodity", "size": 1, "direction": "BUY"}, {"price": 10, "ask": 10, "bid": 9.9})
        trader._ranked_opportunities = lambda: [
            ("SILVER", {"class": "commodity", "size": 1, "direction": "BUY"}, {"price": 10, "ask": 10, "bid": 9.9}),
            ("GOLD", {"class": "commodity", "size": 1, "direction": "SELL"}, {"price": 10, "ask": 10.1, "bid": 10}),
            ("TSLA", {"class": "stock", "size": 1, "direction": "BUY"}, {"price": 10, "ask": 10, "bid": 9.9}),
        ]
        trader._capital_preflight = lambda symbol, size, ticker, cfg=None: {
            "ok": True,
            "reason": "ok",
            "market_status": "TRADEABLE",
            "minimum_deal_size": 1.0,
            "available_balance": 54.34,
        }

        opened = []
        def _shadow(symbol, cfg, ticker):
            opened.append((symbol, cfg["direction"]))
            trader.positions.append(
                CFDPosition(
                    symbol=symbol,
                    deal_id=f"D-{symbol}",
                    epic=f"EPIC-{symbol}",
                    direction=cfg["direction"],
                    size=1,
                    entry_price=10,
                    tp_price=11 if cfg["direction"] == "BUY" else 9,
                    sl_price=9 if cfg["direction"] == "BUY" else 11,
                    asset_class=cfg["class"],
                    current_price=10,
                )
            )
            return object()
        trader._create_shadow = _shadow

        original = __import__("aureon.exchanges.capital_cfd_trader", fromlist=["CAPITAL_FORCE_SLOT_FILL"])
        old_force_slot_fill = original.CAPITAL_FORCE_SLOT_FILL
        try:
            original.CAPITAL_FORCE_SLOT_FILL = False
            trader.tick()
        finally:
            original.CAPITAL_FORCE_SLOT_FILL = old_force_slot_fill

        self.assertEqual(opened, [("SILVER", "BUY"), ("GOLD", "SELL")])

    def test_build_swarm_snapshot_prefers_consensus_leader(self):
        trader = self._build_trader(ClientStub())

        snapshot = trader._build_swarm_snapshot([
            {
                "symbol": "SILVER",
                "direction": "BUY",
                "score": 2.4,
                "change_pct": 1.8,
                "expected_net_profit": 0.14,
                "spread_pct": 0.03,
                "eta_to_target": 0.2,
                "brain_coherence": 0.7,
            },
            {
                "symbol": "GOLD",
                "direction": "SELL",
                "score": 1.8,
                "change_pct": -2.5,
                "expected_net_profit": 0.05,
                "spread_pct": 0.06,
                "eta_to_target": 0.5,
                "brain_coherence": 0.5,
            },
        ])

        self.assertEqual(snapshot["leader"]["symbol"], "SILVER")
        self.assertEqual(snapshot["leader"]["direction"], "BUY")
        self.assertGreaterEqual(snapshot["leader"]["votes"], 3)

    def test_shadow_revenue_priority_prefers_fast_reliable_take_home(self):
        trader = self._build_trader(ClientStub())
        scored = [
            {
                "symbol": "SILVER",
                "direction": "BUY",
                "score": 4.0,
                "expected_net_profit": 0.04,
                "eta_to_target": 0.5,
                "self_confidence": 0.70,
                "timeline_confidence": 0.70,
            },
            {
                "symbol": "GOLD",
                "direction": "BUY",
                "score": 5.0,
                "expected_net_profit": 0.05,
                "eta_to_target": 4.0,
                "self_confidence": 0.55,
                "timeline_confidence": 0.55,
            },
        ]

        trader._apply_shadow_revenue_priority(scored)

        self.assertTrue(scored[0]["shadow_selectable"])
        self.assertFalse(scored[1]["shadow_selectable"])
        self.assertEqual(scored[1]["score"], 0.0)
        self.assertEqual(
            scored[1]["shadow_revenue_priority"]["posture"],
            "bird_in_hand_preferred_over_uncertain_long_eta",
        )

    def test_shadow_revenue_priority_allows_longer_eta_when_take_home_is_caged(self):
        trader = self._build_trader(ClientStub())
        scored = [
            {
                "symbol": "SILVER",
                "direction": "BUY",
                "score": 4.0,
                "expected_net_profit": 0.04,
                "eta_to_target": 0.5,
                "self_confidence": 0.70,
                "timeline_confidence": 0.70,
            },
            {
                "symbol": "GOLD",
                "direction": "BUY",
                "score": 5.0,
                "expected_net_profit": 0.20,
                "eta_to_target": 2.0,
                "self_confidence": 0.82,
                "timeline_confidence": 0.82,
            },
        ]

        trader._apply_shadow_revenue_priority(scored)

        self.assertTrue(scored[1]["shadow_selectable"])
        self.assertEqual(
            scored[1]["shadow_revenue_priority"]["posture"],
            "two_birds_caged_take_home_edge",
        )
        self.assertGreater(scored[1]["shadow_revenue_priority"]["take_home_edge_ratio"], 1.75)

    def test_ranked_opportunities_uses_swarm_order_when_available(self):
        trader = self._build_trader(ClientStub())
        trader._latest_candidate_snapshot = [
            {"symbol": "SILVER", "direction": "BUY", "score": 1.5},
            {"symbol": "GOLD", "direction": "SELL", "score": 2.2},
        ]
        trader._swarm_snapshot = {
            "enabled": True,
            "leader": {"symbol": "SILVER", "direction": "BUY", "swarm_score": 8.0, "votes": 3},
            "votes": [],
            "ranked": [
                {"symbol": "SILVER", "direction": "BUY", "swarm_score": 8.0},
                {"symbol": "GOLD", "direction": "SELL", "swarm_score": 5.0},
            ],
        }
        trader._get_price = lambda symbol: {"price": 10, "bid": 9.9, "ask": 10.1}

        ranked = trader._ranked_opportunities()

        self.assertEqual([(sym, cfg["direction"]) for sym, cfg, _ in ranked], [("SILVER", "BUY"), ("GOLD", "SELL")])

    def test_create_shadow_carries_bird_in_hand_evidence(self):
        trader = self._build_trader(ClientStub())
        trader._latest_candidate_snapshot = [{
            "symbol": "SILVER",
            "direction": "BUY",
            "score": 4.0,
            "expected_net_profit": 0.04,
            "eta_to_target": 0.5,
            "self_confidence": 0.70,
            "shadow_utility_score": 0.056,
            "shadow_revenue_priority": {
                "posture": "bird_in_hand_fast_take_home",
                "expected_net_profit_gbp": 0.04,
                "eta_to_target": 0.5,
                "deadman_ready": True,
                "shadow_selectable": True,
            },
        }]

        shadow = trader._create_shadow(
            "SILVER",
            {"class": "commodity", "size": 1, "tp_pct": 0.75, "sl_pct": 0.45, "direction": "BUY"},
            {"price": 100.0, "ask": 100.05, "bid": 99.95},
        )

        self.assertIsNotNone(shadow)
        assert shadow is not None
        self.assertEqual(shadow.expected_net_profit, 0.04)
        self.assertEqual(shadow.eta_to_target, 0.5)
        self.assertTrue(shadow.deadman_ready)
        self.assertEqual(
            shadow.decision_evidence["shadow_revenue_priority"]["posture"],
            "bird_in_hand_fast_take_home",
        )

    def test_pending_order_plan_attaches_take_profit_and_survival_evidence(self):
        trader = self._build_trader(ClientStub(
            accounts=[{"accountId": "A1", "balance": 1000.0, "available": 1000.0, "currency": "GBP"}],
        ))
        preflight = {
            "ok": True,
            "market_status": "TRADEABLE",
            "price": 100.0,
            "minimum_deal_size": 1.0,
            "margin_factor_pct": 10.0,
            "estimated_margin_required": 10.0,
        }

        context = trader._build_capital_pending_order_context(
            "SILVER",
            "BUY",
            {"class": "commodity", "size": 1, "tp_pct": 0.75, "sl_pct": 0.45},
            {"price": 100.0, "ask": 100.0, "bid": 99.9},
            preflight,
            1.0,
        )

        plan = context["plan"]
        envelope = context["envelope"]
        self.assertLess(plan["level"], 100.0)
        self.assertGreater(plan["profit_level"], plan["level"])
        self.assertIn("profit_level", plan["broker_exit_controls"]["submit_kwargs"])
        self.assertIn("pending_order_submission_disabled", envelope["blockers"])
        self.assertFalse(context["ready_to_submit"])

    def test_pending_order_survival_blocks_hundred_bids_if_all_fill(self):
        trader = self._build_trader(ClientStub(
            accounts=[{"accountId": "A1", "balance": 1000.0, "available": 1000.0, "currency": "GBP"}],
        ))
        planned = [
            {
                "symbol": f"AAPL{i % 3}",
                "direction": "BUY",
                "size": 1.0,
                "level": 100.0,
                "notional": 100.0,
                "estimated_margin_required": 20.0,
                "profit_level": 101.0,
                "blockers": [],
            }
            for i in range(100)
        ]

        envelope = trader._build_capital_pending_order_survival_envelope(
            planned,
            existing_working_orders=[],
        )

        self.assertTrue(envelope["blocked"])
        self.assertEqual(envelope["pending_count_after"], 100)
        self.assertIn("max_pending_working_orders", envelope["blockers"])
        self.assertIn("pending_margin_budget_limit", envelope["blockers"])

    def test_submit_pending_order_requires_survival_envelope_green(self):
        trader = self._build_trader(ClientStub())
        plan = {
            "symbol": "SILVER",
            "direction": "BUY",
            "size": 1.0,
            "level": 100.0,
            "order_type": "LIMIT",
            "broker_exit_controls": {"submit_kwargs": {"profit_level": 101.0}},
        }
        blocked = {"can_submit_pending_orders": False, "blockers": ["max_pending_working_orders"]}

        result = trader._submit_capital_pending_order(plan, blocked)

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "pending_survival_envelope_blocked")

    def test_apply_intelligence_overlays_can_block_candidate_via_orchestrator(self):
        class OrchestratorStub:
            def gate_pre_trade(self, symbol, side):
                if symbol == "SILVER":
                    return False, "confidence_too_low", {}
                return True, "ok", {}

        trader = self._build_trader(ClientStub())
        trader.orchestrator = OrchestratorStub()
        trader.timeline_oracle = None
        trader.harmonic_fusion = None
        scored = [
            {"symbol": "SILVER", "direction": "BUY", "score": 2.0, "price": 100.0, "change_pct": 1.5},
            {"symbol": "GOLD", "direction": "SELL", "score": 1.5, "price": 100.0, "change_pct": -1.2},
        ]

        trader._apply_intelligence_overlays(scored)

        self.assertEqual(scored[0]["score"], 0.0)
        self.assertIn("orchestrator_gate", scored[0]["intel_reason"])
        self.assertTrue(scored[1]["score"] > 0.0)

    def test_can_open_candidate_skips_symbol_on_active_rejection_cooldown(self):
        trader = self._build_trader(ClientStub())

        trader._record_rejection("SILVER", "BUY", "preflight_failed")

        self.assertFalse(trader._can_open_candidate("SILVER", "BUY"))
        self.assertTrue(trader._can_open_candidate("SILVER", "SELL"))

    def test_build_lane_snapshot_prefers_validated_shadow_as_next_in_line(self):
        trader = self._build_trader(ClientStub())
        trader.positions = [
            CFDPosition(
                symbol="SILVER",
                deal_id="DBUY",
                epic="EPIC-SILVER",
                direction="BUY",
                size=1,
                entry_price=10,
                tp_price=11,
                sl_price=9,
                asset_class="commodity",
                current_price=10,
            )
        ]
        validated_sell = CFDShadowTrade(
            symbol="GOLD",
            direction="SELL",
            asset_class="commodity",
            size=1,
            entry_price=10,
            target_move_pct=0.1,
            score=2.0,
        )
        validated_sell.validated = True
        queued_buy = CFDShadowTrade(
            symbol="TSLA",
            direction="BUY",
            asset_class="stock",
            size=1,
            entry_price=10,
            target_move_pct=0.1,
            score=1.0,
        )
        trader.shadow_trades = [queued_buy, validated_sell]

        lanes = trader._build_lane_snapshot()

        self.assertEqual(lanes["BUY"]["position_symbol"], "SILVER")
        self.assertEqual(lanes["SELL"]["validated_shadow_symbol"], "GOLD")
        self.assertEqual(lanes["SELL"]["next_action"], "promote_validated_shadow")

    def test_open_position_accepts_verified_live_deal_after_short_delay(self):
        live_position = {
            "position": {
                "dealId": "DDELAY",
                "direction": "BUY",
                "size": 1,
                "level": 7282.6,
            },
            "market": {
                "epic": "CS.D.SILVER.CFD.IP",
                "symbol": "SILVER",
                "bid": 7249.8,
                "offer": 7251.8,
                "instrumentType": "COMMODITY",
            },
        }
        trader = self._build_trader(ClientStub(
            open_result={"dealReference": "REF-DELAY"},
            confirm_result={"dealId": "DDELAY", "level": 7282.6},
            accounts=[{"accountId": "A1", "balance": 50000.0, "available": 50000.0, "currency": "GBP"}],
        ))
        trader.client._position_batches = [[], [], [live_position]]

        result = trader._open_position(
            "SILVER",
            {"class": "commodity", "size": 1, "tp_pct": 0.75, "sl_pct": 0.45},
            {"price": 7282.6, "ask": 7282.6, "epic": "CS.D.SILVER.CFD.IP"},
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.deal_id, "DDELAY")

    def test_open_position_requires_exchange_validation(self):
        trader = self._build_trader(ClientStub(
            positions=[],
            open_result={"dealReference": "REF-NO-LIVE"},
            confirm_result={"dealId": "D-NO-LIVE", "level": 7282.6},
        ))

        result = trader._open_position(
            "SILVER",
            {"class": "commodity", "size": 1, "tp_pct": 0.75, "sl_pct": 0.45},
            {"price": 7282.6, "ask": 7282.6, "epic": "CS.D.SILVER.CFD.IP"},
        )

        self.assertIsNone(result)
        self.assertEqual(trader.positions, [])
        self.assertEqual(trader.stats["trades_opened"], 0.0)

    def test_open_position_stops_immediately_on_capital_reject_reason(self):
        trader = self._build_trader(ClientStub(
            positions=[],
            open_result={"dealReference": "REF-REJECT"},
            confirm_result={
                "dealId": "D-REJECT",
                "dealStatus": "REJECTED",
                "rejectReason": "RISK_CHECK",
                "status": "DELETED",
            },
            accounts=[{"accountId": "A1", "balance": 50000.0, "available": 50000.0, "currency": "GBP"}],
        ))

        result = trader._open_position(
            "SILVER",
            {"class": "commodity", "size": 1, "tp_pct": 0.75, "sl_pct": 0.45},
            {"price": 7282.6, "ask": 7282.6, "epic": "CS.D.SILVER.CFD.IP"},
        )

        self.assertIsNone(result)
        self.assertIn("RISK_CHECK", trader._latest_order_error)

    def test_sync_positions_from_exchange_rebuilds_live_position(self):
        trader = CapitalCFDTrader.__new__(CapitalCFDTrader)
        trader.client = ClientStub(positions=[{
            "position": {
                "dealId": "D1",
                "direction": "BUY",
                "size": 1,
                "level": 7282.6,
            },
            "market": {
                "epic": "CS.D.SILVER.CFD.IP",
                "symbol": "SILVER",
                "bid": 7249.8,
                "offer": 7251.8,
                "instrumentType": "COMMODITY",
            },
        }])
        trader.positions = []
        trader._dtp_trackers = {}
        trader._last_exchange_sync = 0.0
        trader._required_tp_pct_for_profit = lambda price, size: (CAPITAL_MIN_PROFIT_GBP / max(price * size, 0.0001)) * 100.0

        trader._sync_positions_from_exchange(force=True)

        self.assertEqual(len(trader.positions), 1)
        pos = trader.positions[0]
        self.assertEqual(pos.symbol, "SILVER")
        self.assertEqual(pos.deal_id, "D1")
        self.assertEqual(pos.direction, "BUY")
        self.assertGreater(pos.tp_price, pos.entry_price)

    def test_open_position_accepts_verified_live_deal(self):
        live_position = {
            "position": {
                "dealId": "DOPEN",
                "direction": "BUY",
                "size": 1,
                "level": 7282.6,
            },
            "market": {
                "epic": "CS.D.SILVER.CFD.IP",
                "symbol": "SILVER",
                "bid": 7249.8,
                "offer": 7251.8,
                "instrumentType": "COMMODITY",
            },
        }
        trader = self._build_trader(ClientStub(
            positions=[live_position],
            open_result={"dealReference": "REF1"},
            confirm_result={"dealId": "DOPEN", "level": 7282.6},
            accounts=[{"accountId": "A1", "balance": 50000.0, "available": 50000.0, "currency": "GBP"}],
        ))

        result = trader._open_position(
            "SILVER",
            {"class": "commodity", "size": 1, "tp_pct": 0.75, "sl_pct": 0.45},
            {"price": 7282.6, "ask": 7282.6, "epic": "CS.D.SILVER.CFD.IP"},
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.deal_id, "DOPEN")
        self.assertEqual(len(trader.positions), 1)
        self.assertEqual(trader.stats["trades_opened"], 1.0)

    def test_open_position_accepts_verified_live_sell_deal(self):
        live_position = {
            "position": {
                "dealId": "DSELL",
                "direction": "SELL",
                "size": 1,
                "level": 7249.8,
            },
            "market": {
                "epic": "CS.D.SILVER.CFD.IP",
                "symbol": "SILVER",
                "bid": 7249.8,
                "offer": 7251.8,
                "instrumentType": "COMMODITY",
            },
        }
        client = ClientStub(
            positions=[live_position],
            open_result={"dealReference": "REFSELL"},
            confirm_result={"dealId": "DSELL", "level": 7249.8},
            accounts=[{"accountId": "A1", "balance": 50000.0, "available": 50000.0, "currency": "GBP"}],
        )
        trader = self._build_trader(client)

        result = trader._open_position(
            "SILVER",
            {"class": "commodity", "size": 1, "tp_pct": 0.75, "sl_pct": 0.45, "direction": "SELL"},
            {"price": 7250.8, "ask": 7251.8, "bid": 7249.8, "epic": "CS.D.SILVER.CFD.IP"},
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.direction, "SELL")
        self.assertLess(result.tp_price, result.entry_price)
        self.assertGreater(result.sl_price, result.entry_price)
        self.assertEqual(client.order_calls[-1][:3], ("SILVER", "SELL", 1))
        self.assertIn("profit_level", client.order_calls[-1][3])

    def test_capital_live_expansion_stress_reaches_broker_submit_path(self):
        class DynamicClientStub(ClientStub):
            def __init__(self):
                super().__init__(
                    positions=[],
                    accounts=[{"accountId": "A1", "balance": 100000.0, "available": 100000.0, "currency": "GBP"}],
                )
                self._sequence = 0

            def _resolve_market(self, symbol: str):
                return {"epic": f"CS.D.{symbol}.CFD.IP", "symbol": symbol}

            def _get_market_snapshot(self, epic: str):
                symbol = epic.split(".")[2] if "." in epic else "MARKET"
                return {
                    "instrument": {"epic": epic, "name": symbol},
                    "snapshot": {"marketStatus": "TRADEABLE", "bid": 99.95, "offer": 100.05},
                    "dealingRules": {"minDealSize": {"value": 1}},
                    "depositBands": [{"min": 0, "max": 999999999, "margin": 5.0}],
                }

            def place_market_order(self, symbol: str, side: str, size: float, **kwargs):
                self._sequence += 1
                deal_id = f"DSTRESS{self._sequence}"
                self.order_calls.append((symbol, side.upper(), size, kwargs))
                self._open_result = {"dealReference": f"REF-{deal_id}", "dealId": deal_id}
                self._confirm_result = {"dealId": deal_id, "level": 100.0}
                self._positions.append({
                    "position": {
                        "dealId": deal_id,
                        "direction": side.upper(),
                        "size": size,
                        "level": 100.0,
                    },
                    "market": {
                        "epic": f"CS.D.{symbol}.CFD.IP",
                        "symbol": symbol,
                        "bid": 99.95,
                        "offer": 100.05,
                        "instrumentType": "SHARES",
                    },
                })
                return dict(self._open_result)

        trader = self._build_trader(DynamicClientStub())
        trader._central_beat_regime = {"bias": "BUY", "confidence": 0.5}
        trader._central_beat_symbols = {
            "ALPHA": {"side": "BUY", "strength": 0.66, "support_count": 3},
            "BRAVO": {"side": "BUY", "strength": 0.70, "support_count": 3},
            "CHARLIE": {"side": "BUY", "strength": 0.74, "support_count": 4},
        }
        trader._latest_candidate_snapshot = [
            {
                "symbol": "ALPHA",
                "direction": "BUY",
                "score": 6.4,
                "self_confidence": 0.64,
                "timeline_action": "buy",
                "timeline_confidence": 0.64,
                "fusion_global_coherence": 0.45,
                "eta_to_target": 8.0,
            },
            {
                "symbol": "BRAVO",
                "direction": "BUY",
                "score": 7.1,
                "self_confidence": 0.71,
                "timeline_action": "buy",
                "timeline_confidence": 0.71,
                "fusion_global_coherence": 0.50,
                "eta_to_target": 7.0,
            },
            {
                "symbol": "CHARLIE",
                "direction": "BUY",
                "score": 8.0,
                "self_confidence": 0.80,
                "timeline_action": "buy",
                "timeline_confidence": 0.80,
                "fusion_global_coherence": 0.55,
                "eta_to_target": 5.5,
            },
            {
                "symbol": "DELTA",
                "direction": "BUY",
                "score": 5.0,
                "self_confidence": 0.50,
                "timeline_action": "buy",
                "timeline_confidence": 0.50,
                "fusion_global_coherence": 0.42,
                "eta_to_target": 9.0,
            },
        ]

        opened = []
        for symbol in ("ALPHA", "BRAVO", "CHARLIE"):
            opened.append(trader._open_position(
                symbol,
                {"class": "stock", "size": 1, "tp_pct": 0.75, "sl_pct": 0.45, "direction": "BUY"},
                {"price": 100.0, "ask": 100.05, "bid": 99.95, "epic": f"CS.D.{symbol}.CFD.IP"},
            ))

        blocked = trader._open_position(
            "DELTA",
            {"class": "stock", "size": 1, "tp_pct": 0.75, "sl_pct": 0.45, "direction": "BUY"},
            {"price": 100.0, "ask": 100.05, "bid": 99.95, "epic": "CS.D.DELTA.CFD.IP"},
        )

        self.assertEqual([pos.deal_id for pos in opened if pos is not None], ["DSTRESS1", "DSTRESS2", "DSTRESS3"])
        self.assertIsNone(blocked)
        self.assertEqual(len(trader.client.order_calls), 3)
        self.assertEqual(trader.stats["trades_opened"], 3.0)
        self.assertTrue(trader._capital_trade_evidence["act"]["evidence_complete"])
        self.assertIn("weaker_than_previous_live_candidate", trader._latest_order_error)

    def test_monitor_keeps_position_when_close_fails_and_exchange_still_reports_it(self):
        trader = CapitalCFDTrader.__new__(CapitalCFDTrader)
        trader.client = ClientStub(
            positions=[{"position": {"dealId": "D2"}}],
            close_result={"success": False, "error": "rejected"},
            fallback_result={"rejected": True, "error": "blocked"},
        )
        trader.positions = [
            CFDPosition(
                symbol="SILVER",
                deal_id="D2",
                epic="CS.D.SILVER.CFD.IP",
                direction="BUY",
                size=1,
                entry_price=7282.6,
                tp_price=7300.0,
                sl_price=7200.0,
                asset_class="commodity",
                current_price=7305.0,
            )
        ]
        trader.stats = {
            "trades_opened": 0.0,
            "trades_closed": 0.0,
            "winning_trades": 0.0,
            "losing_trades": 0.0,
            "total_pnl_gbp": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
        }
        trader._recent_closed_trades = []
        trader._latest_monitor_line = ""
        trader._dtp_trackers = {}

        closed = trader._monitor_positions()

        self.assertEqual(closed, [])
        self.assertEqual(len(trader.positions), 1)
        self.assertEqual(trader.positions[0].deal_id, "D2")

    def test_monitor_profit_only_mode_does_not_close_losing_position(self):
        old_flag = CFD_FLAGS["profit_only_closes"]
        CFD_FLAGS["profit_only_closes"] = True
        try:
            trader = CapitalCFDTrader.__new__(CapitalCFDTrader)
            trader.client = ClientStub(close_result={"success": True})
            trader.positions = [
                CFDPosition(
                    symbol="SILVER",
                    deal_id="D3",
                    epic="CS.D.SILVER.CFD.IP",
                    direction="BUY",
                    size=1,
                    entry_price=7282.6,
                    tp_price=7337.2,
                    sl_price=7249.8,
                    asset_class="commodity",
                    current_price=7240.0,
                )
            ]
            trader._recent_closed_trades = []
            trader._latest_monitor_line = ""
            trader._dtp_trackers = {}

            closed = trader._monitor_positions()

            self.assertEqual(closed, [])
            self.assertEqual(len(trader.positions), 1)
            self.assertIn("mode=profit_only", trader._latest_monitor_line)
        finally:
            CFD_FLAGS["profit_only_closes"] = old_flag

    def test_monitor_profit_only_mode_closes_profitable_position(self):
        old_flag = CFD_FLAGS["profit_only_closes"]
        CFD_FLAGS["profit_only_closes"] = True
        try:
            trader = CapitalCFDTrader.__new__(CapitalCFDTrader)
            trader.client = ClientStub(close_result={"success": True})
            trader.positions = [
                CFDPosition(
                    symbol="SILVER",
                    deal_id="D4",
                    epic="CS.D.SILVER.CFD.IP",
                    direction="BUY",
                    size=1,
                    entry_price=7282.6,
                    tp_price=7330.0,
                    sl_price=7249.8,
                    asset_class="commodity",
                    current_price=7335.0,
                )
            ]
            trader.stats = {
                "trades_opened": 0.0,
                "trades_closed": 0.0,
                "winning_trades": 0.0,
                "losing_trades": 0.0,
                "total_pnl_gbp": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
            }
            trader._recent_closed_trades = []
            trader._latest_monitor_line = ""
            trader._dtp_trackers = {}

            closed = trader._monitor_positions()

            self.assertEqual(len(closed), 1)
            self.assertEqual(trader.positions, [])
            self.assertGreater(closed[0]["net_pnl"], 0.0)
        finally:
            CFD_FLAGS["profit_only_closes"] = old_flag

    def test_monitor_positions_closes_on_penny_profit_before_static_tp(self):
        class EngineStub:
            @staticmethod
            def get_threshold(exchange, entry_value):
                return type("Threshold", (), {"win_gte": 0.05, "win_pct": 0.49})()

        old_profit_only = CFD_FLAGS["profit_only_closes"]
        old_penny = CFD_FLAGS["penny_take_profit"]
        CFD_FLAGS["profit_only_closes"] = True
        CFD_FLAGS["penny_take_profit"] = True
        try:
            trader = self._build_trader(ClientStub(close_result={"success": True}))
            trader.penny_engine = EngineStub()
            trader.positions = [
                CFDPosition(
                    symbol="SILVER",
                    deal_id="D5P",
                    epic="CS.D.SILVER.CFD.IP",
                    direction="BUY",
                    size=1,
                    entry_price=100.0,
                    tp_price=101.0,
                    sl_price=99.0,
                    asset_class="commodity",
                    current_price=100.08,
                )
            ]

            closed = trader._monitor_positions()

            self.assertEqual(len(closed), 1)
            self.assertEqual(trader.positions, [])
            self.assertIn("PENNY_TP", closed[0]["reason"])
        finally:
            CFD_FLAGS["profit_only_closes"] = old_profit_only
            CFD_FLAGS["penny_take_profit"] = old_penny

    def test_monitor_positions_fast_profit_capture_closes_tradeable_profit(self):
        trader = self._build_trader(ClientStub(
            close_result={"success": True},
            market_snapshot={
                "instrument": {"epic": "CS.D.SILVER.CFD.IP", "name": "Silver"},
                "snapshot": {"marketStatus": "TRADEABLE", "bid": 100.05, "offer": 100.07},
                "dealingRules": {"minDealSize": {"value": 1}},
            },
        ))
        trader.positions = [
            CFDPosition(
                symbol="SILVER",
                deal_id="DFAST",
                epic="CS.D.SILVER.CFD.IP",
                direction="BUY",
                size=1,
                entry_price=100.0,
                tp_price=101.0,
                sl_price=99.0,
                asset_class="commodity",
                opened_at=time.time() - 5.0,
                current_price=100.06,
            )
        ]

        closed = trader._monitor_positions()

        self.assertEqual(len(closed), 1)
        self.assertEqual(trader.positions, [])
        self.assertIn("FAST_PROFIT_CAPTURE", closed[0]["reason"])
        self.assertGreater(closed[0]["net_pnl"], 0.0)
        self.assertTrue(closed[0]["fast_profit_capture"]["market_active_for_close"])
        self.assertEqual(trader._last_fast_profit_capture["ready_to_capture"], 1)

    def test_monitor_positions_fast_profit_capture_holds_when_market_closed(self):
        trader = self._build_trader(ClientStub(
            close_result={"success": True},
            market_snapshot={
                "instrument": {"epic": "CS.D.SILVER.CFD.IP", "name": "Silver"},
                "snapshot": {"marketStatus": "CLOSED", "bid": 100.05, "offer": 100.07},
                "dealingRules": {"minDealSize": {"value": 1}},
            },
        ))
        trader.positions = [
            CFDPosition(
                symbol="SILVER",
                deal_id="DCLOSED",
                epic="CS.D.SILVER.CFD.IP",
                direction="BUY",
                size=1,
                entry_price=100.0,
                tp_price=101.0,
                sl_price=99.0,
                asset_class="commodity",
                opened_at=time.time() - 5.0,
                current_price=100.06,
            )
        ]

        closed = trader._monitor_positions()

        self.assertEqual(closed, [])
        self.assertEqual(len(trader.positions), 1)
        latest_check = trader._last_fast_profit_capture["checks"][0]
        self.assertFalse(latest_check["market_active_for_close"])
        self.assertIn("market_not_active:CLOSED", latest_check["reason"])

    def test_score_symbol_uses_central_beat_alignment(self):
        trader = self._build_trader(ClientStub())
        trader._effective_tp_pct = lambda price, size, cfg: 0.5
        trader._central_beat_symbols = {
            "SILVER": {"side": "BUY", "support_count": 3, "strength": 0.9},
        }
        trader._central_beat_regime = {"bias": "BUY", "confidence": 0.8}
        ticker = {"price": 100.0, "bid": 99.99, "ask": 100.01, "change_pct": 0.4, "high": 101.0, "low": 99.0}
        cfg = {"max_spread_pct": 0.01, "momentum_threshold": 0.1, "size": 1.0}
        boosted_score, direction = trader._score_symbol("SILVER", cfg, ticker)

        trader._central_beat_symbols = {}
        trader._central_beat_regime = {}
        trader._prev_change_pct = {}
        plain_score, _ = trader._score_symbol("SILVER", cfg, ticker)

        self.assertEqual(direction, "BUY")
        self.assertGreater(boosted_score, plain_score)

    def test_fill_live_monitoring_slots_opens_buy_and_sell_when_risk_preflight_passes(self):
        trader = self._build_trader(ClientStub())
        trader._last_slot_fill_attempt = {"BUY": 0.0, "SELL": 0.0}
        trader._capital_preflight = lambda symbol, size, ticker, cfg=None: {
            "ok": True,
            "reason": "ok",
            "price": ticker.get("price"),
            "bid": ticker.get("bid"),
            "ask": ticker.get("ask"),
            "requested_size": size,
            "expected_net_profit": 0.01,
            "estimated_margin_required": 0.01,
            "margin_factor_pct": 1.0,
        }
        opened = []
        class Opened:
            def __init__(self, deal_id):
                self.deal_id = deal_id
        trader._prepare_live_trade_candidate = lambda symbol, direction, cfg, ticker, requested_size, action: {
            "ok": True,
            "cfg": dict(cfg),
            "size": requested_size,
        }
        trader._open_position = lambda symbol, cfg, ticker: opened.append((symbol, cfg["direction"])) or Opened(f"{symbol}-{cfg['direction']}")
        trader._latest_candidate_snapshot = [
            {"symbol": "SILVER", "direction": "BUY", "score": 0.0},
            {"symbol": "GOLD", "direction": "SELL", "score": 0.0},
        ]
        trader._prices = {
            "SILVER": {"price": 100.0, "bid": 99.9, "ask": 100.1},
            "GOLD": {"price": 200.0, "bid": 199.9, "ask": 200.1},
        }

        result = trader._fill_live_monitoring_slots(100.0)

        self.assertTrue(result)
        self.assertEqual(opened, [("SILVER", "BUY"), ("GOLD", "SELL")])

    def test_capital_risk_envelope_blocks_symbol_concentration(self):
        trader = self._build_trader(ClientStub(accounts=[
            {"accountId": "A1", "balance": 100.0, "available": 100.0, "currency": "GBP"}
        ]))

        envelope = trader._build_capital_risk_envelope(candidate={
            "symbol": "AAPL",
            "direction": "BUY",
            "size": 1.0,
            "price": 50.0,
            "asset_class": "stocks",
            "estimated_margin_required": 10.0,
            "margin_factor_pct": 20.0,
            "cfg": {"class": "stocks", "sl_pct": 0.25},
        })

        self.assertFalse(envelope["new_entries_allowed"])
        self.assertIn("single_symbol_concentration_limit", envelope["blockers"])

    def test_prepare_live_trade_blocks_cross_exchange_waveform_contradiction(self):
        trader = self._build_trader(ClientStub(accounts=[
            {"accountId": "A1", "balance": 10000.0, "available": 10000.0, "currency": "GBP"}
        ]))
        trader._central_beat_symbols = {
            "GOLD": {"side": "SELL", "strength": 0.9, "support_count": 3}
        }
        trader._latest_candidate_snapshot = [{
            "symbol": "GOLD",
            "direction": "BUY",
            "score": 8.0,
            "self_confidence": 0.8,
            "eta_to_target": 0.5,
        }]
        ticker = {"price": 100.0, "bid": 99.9, "ask": 100.1}
        cfg = {"class": "commodities", "size": 0.01, "tp_pct": 0.2, "sl_pct": 0.25}
        trader._capital_preflight = lambda symbol, size, ticker, cfg=None: {
            "ok": True,
            "reason": "ok",
            "requested_size": size,
            "price": ticker["price"],
            "bid": ticker["bid"],
            "ask": ticker["ask"],
            "minimum_deal_size": 0.0,
            "expected_net_profit": 0.10,
            "estimated_margin_required": 0.10,
            "margin_factor_pct": 10.0,
        }

        prepared = trader._prepare_live_trade_candidate("GOLD", "BUY", cfg, ticker, 0.01, action="open_live")

        self.assertFalse(prepared["ok"])
        self.assertIn("central_beat_symbol_contradiction", prepared["reason"])
        self.assertFalse(trader._capital_trade_evidence["act"]["approved"])

    def test_confidence_ratchet_blocks_weaker_follow_up(self):
        trader = self._build_trader(ClientStub())
        trader._capital_confidence_ratchet = {
            "schema_version": 1,
            "enabled": True,
            "last_live_candidate": {
                "symbol": "GOLD",
                "direction": "BUY",
                "confidence": 0.90,
                "eta_to_target": 0.5,
                "risk_adjusted_score": 1.8,
            },
        }

        check = trader._build_confidence_ratchet_check({
            "symbol": "SILVER",
            "direction": "BUY",
            "confidence": 0.60,
            "eta_to_target": 1.2,
            "risk_adjusted_score": 0.5,
        })

        self.assertFalse(check["ok"])
        self.assertIn("weaker_than_previous_live_candidate", check["reason"])

    def test_open_position_blocks_insufficient_margin_before_exchange_order(self):
        client = ClientStub(accounts=[
            {"accountId": "A1", "balance": 1.0, "available": 1.0, "currency": "GBP"}
        ], market_snapshot={
            "instrument": {"epic": "CS.D.SILVER.CFD.IP", "name": "Silver"},
            "snapshot": {"marketStatus": "TRADEABLE", "bid": 99.9, "offer": 100.1},
            "dealingRules": {"minDealSize": {"value": 0.01}, "marginFactor": {"unit": "PERCENTAGE", "value": 5.0}},
        })
        trader = self._build_trader(client)
        ticker = {"price": 100.0, "bid": 99.9, "ask": 100.1, "epic": "CS.D.SILVER.CFD.IP"}
        cfg = {"class": "commodities", "size": 1.0, "tp_pct": 0.2, "sl_pct": 0.25, "direction": "BUY"}

        pos = trader._open_position("SILVER", cfg, ticker)

        self.assertIsNone(pos)
        self.assertEqual(client.order_calls, [])
        self.assertIn("live candidate blocked", trader._latest_order_error.lower())

    def test_no_loss_hold_queue_reports_losing_positions(self):
        trader = self._build_trader(ClientStub())
        trader.positions = [
            CFDPosition(
                symbol="SILVER",
                deal_id="D1",
                epic="CS.D.SILVER.CFD.IP",
                direction="BUY",
                size=1.0,
                entry_price=100.0,
                tp_price=101.0,
                sl_price=99.0,
                asset_class="commodities",
                current_price=99.5,
            )
        ]

        queue = trader._build_no_loss_hold_queue()

        self.assertTrue(queue["enabled"])
        self.assertEqual(queue["losing_position_count"], 1)
        self.assertLess(queue["total_unrealized_negative_gbp"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
