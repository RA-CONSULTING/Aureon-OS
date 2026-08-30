"""Offline provenance regressions for the unified market trader."""

from __future__ import annotations

import importlib
import io
import os
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_LLM_OFFLINE", "1")
os.environ.setdefault("AUREON_DISABLE_LLM_HTTP", "1")


def _offline_request(*_args, **_kwargs):
    raise OSError("network is forbidden in this offline test module")


with (
    patch("requests.sessions.Session.request", side_effect=_offline_request),
    patch("urllib.request.urlopen", side_effect=_offline_request),
    patch("urllib3.util.connection.create_connection", side_effect=_offline_request),
    patch("httpx.Client.request", side_effect=_offline_request),
    patch("httpx.AsyncClient.request", side_effect=_offline_request),
    redirect_stdout(io.StringIO()),
    redirect_stderr(io.StringIO()),
):
    trader_module = importlib.import_module("aureon.exchanges.unified_market_trader")


@pytest.fixture(autouse=True)
def _forbid_network_during_tests():
    with (
        patch("requests.sessions.Session.request", side_effect=_offline_request),
        patch("urllib.request.urlopen", side_effect=_offline_request),
        patch("urllib3.util.connection.create_connection", side_effect=_offline_request),
        patch("httpx.Client.request", side_effect=_offline_request),
        patch("httpx.AsyncClient.request", side_effect=_offline_request),
    ):
        yield


def _trader():
    trader = trader_module.UnifiedMarketTrader.__new__(trader_module.UnifiedMarketTrader)
    trader.dry_run = False
    trader.kraken = None
    trader.alpaca = None
    trader.binance = None
    trader._binance_diag = {}
    trader._api_governor = trader_module.ExchangeCallGovernor()
    trader._dynamic_intelligence_budget = {}
    trader._dynamic_probe_interval = lambda _venue: 1.0
    trader._dynamic_exchange_budget = lambda _venue: {"role": "test_budget"}
    trader._stream_price_ticker = lambda _symbol, max_age_sec=trader_module.STREAM_CACHE_MAX_AGE_SEC: None
    return trader


def _market_inputs(timestamp: float | None = None):
    observed = time.time() if timestamp is None else timestamp
    row = {
        "symbol": "BTCUSD",
        "side": "BUY",
        "confidence": 0.82,
        "support_count": 2,
        "reference_price": 50_000.0,
        "change_pct": 1.1,
        "model_alignment": True,
        "data_status": "live",
        "actionable": True,
    }
    central = {
        "generated_at": datetime.fromtimestamp(observed).isoformat(),
        "sources": [{"source": "alpaca", "ready": True, "actionable": True, "data_status": "live"}],
        "symbols": {"BTCUSD": dict(row)},
    }
    return central, {"active_order_flow": [dict(row)]}


def _complete_fill(now: float | None = None):
    observed = time.time() if now is None else now
    return {
        "order_id": "K-FILL-1",
        "status": "FILLED",
        "data_status": "live",
        "truth_status": "real_observed",
        "submitted": True,
        "fill_receipt_complete": True,
        "eligible_for_learning": True,
        "generated_values": False,
        "provider_timestamp": observed,
        "filled_qty": "2",
        "filled_avg_price": "10",
        "filled_notional": "20",
        "fee": "0.02",
    }


def test_target_passes_exact_hardened_validator():
    from scripts.validation.validate_real_data_contract import scan_text_file

    root = Path(__file__).resolve().parents[1]
    target = root / "aureon" / "exchanges" / "unified_market_trader.py"
    assert scan_text_file(target, root) == []


def test_governor_preserves_original_receipt_age_and_rejects_old_cache():
    governor = trader_module.ExchangeCallGovernor()
    key = "alpaca:ticker:BTC/USD"
    governor._cache[key] = {"at": time.time() - 120.0, "value": {"price": 100.0}}

    receipt = governor.call_with_receipt(
        "alpaca",
        "quotes",
        key,
        lambda: pytest.fail("old cache must not trigger a provider call in this branch"),
        min_interval_sec=1_000.0,
        stale_ttl_sec=30.0,
    )

    assert receipt["status"] == "no_data"
    assert receipt["reason"] == "provider_receipt_stale_or_future"


def test_governor_never_reuses_future_dated_cache_as_fresh():
    governor = trader_module.ExchangeCallGovernor()
    key = "alpaca:ticker:ETH/USD"
    governor._cache[key] = {"at": time.time() + 120.0, "value": {"price": 1.0}}
    calls = []

    receipt = governor.call_with_receipt(
        "alpaca",
        "quotes",
        key,
        lambda: calls.append("provider") or {"price": 200.0},
        min_interval_sec=1_000.0,
        stale_ttl_sec=30.0,
    )

    assert calls == ["provider"]
    assert receipt["status"] == "live"
    assert receipt["value"] == {"price": 200.0}
    assert receipt["from_cache"] is False


def test_alpaca_snapshot_uses_fresh_finite_receipt_and_cache_without_second_call():
    now = time.time()

    class AlpacaStub:
        init_error = ""
        is_authenticated = True

        def __init__(self):
            self.calls = 0

        def get_ticker(self, _symbol):
            self.calls += 1
            return {"price": "100.5", "change_pct": "1.25", "timestamp": now}

    trader = _trader()
    trader.alpaca = AlpacaStub()

    first = trader._extract_alpaca_source_snapshot(["BTCUSD"])
    second = trader._extract_alpaca_source_snapshot(["BTCUSD"])

    assert first["status"] == "live"
    assert first["symbols"]["BTCUSD"]["price"] == 100.5
    assert first["symbols"]["BTCUSD"]["timestamp_kind"] == "provider_event"
    assert second["symbols"]["BTCUSD"]["from_cache"] is True
    assert trader.alpaca.calls == 1


@pytest.mark.parametrize(
    "ticker_template,timestamp_offset,reason",
    [
        ({"change_pct": "1.0"}, 0.0, "missing_or_malformed_provider_price_or_change"),
        ({"price": "nan", "change_pct": "1.0"}, 0.0, "missing_or_malformed_provider_price_or_change"),
        ({"price": "100", "change_pct": "1.0"}, -300.0, "stale_provider_timestamp"),
        ({"price": "100", "change_pct": "1.0"}, 60.0, "future_provider_timestamp"),
    ],
)
def test_alpaca_snapshot_rejects_missing_nonfinite_stale_and_future_tickers(
    ticker_template, timestamp_offset, reason
):
    ticker = {**ticker_template, "timestamp": time.time() + timestamp_offset}
    trader = _trader()
    trader.alpaca = SimpleNamespace(init_error="", is_authenticated=True, get_ticker=lambda _symbol: dict(ticker))

    snapshot = trader._extract_alpaca_source_snapshot(["BTCUSD"])

    assert snapshot["status"] == "no_data"
    assert snapshot["actionable"] is False
    assert reason in snapshot["failure_reasons"]


def test_binance_snapshot_rejects_future_receipt_and_missing_price():
    trader = _trader()
    trader._binance_diag = {"network_ok": True}
    trader.binance = SimpleNamespace(
        get_24h_ticker=lambda _symbol: {
            "priceChangePercent": "2.0",
            "closeTime": int((time.time() + 60.0) * 1000),
        }
    )

    snapshot = trader._extract_binance_source_snapshot(["BTCUSD"])

    assert snapshot["status"] == "no_data"
    assert snapshot["symbols"] == {}
    assert "future_provider_timestamp" in snapshot["failure_reasons"]


def test_hnc_metrics_require_fresh_cycle_source_and_complete_finite_row():
    trader = _trader()
    central, order_flow = _market_inputs()

    live = trader._hnc_source_metrics(central, order_flow)
    stale = trader._hnc_source_metrics(*_market_inputs(time.time() - trader_module.CENTRAL_BEAT_STALE_AFTER_SEC - 1.0))
    future = trader._hnc_source_metrics(*_market_inputs(time.time() + 60.0))
    central["sources"][0]["stale"] = True
    no_source = trader._hnc_source_metrics(central, order_flow)

    assert live["passed"] is True
    assert live["data_status"] == "live"
    assert stale["status"] == "no_data"
    assert future["status"] == "no_data"
    assert no_source["status"] == "no_data"
    assert "fresh_provider_sources_unavailable" in no_source["blockers"]


def test_auris_nodes_do_not_evaluate_from_missing_market_values():
    trader = _trader()
    incomplete = trader._build_auris_node_proof({"volatility": 0.2, "momentum": 0.1})
    complete = trader._build_auris_node_proof(
        {
            "volatility": 0.2,
            "momentum": 0.1,
            "volume": 0.7,
            "spread": 0.05,
            "route_unity": 0.75,
            "model_alignment": 0.8,
            "confidence": 0.82,
        }
    )

    assert incomplete["status"] == "no_data"
    assert incomplete["evaluated"] is False
    assert incomplete["nodes"] == {}
    assert complete["evaluated"] is True
    assert complete["node_count"] == 9


def test_hnc_operating_cycle_denies_action_when_evidence_is_missing():
    trader = _trader()
    proof = trader._build_hnc_cognitive_proof(
        {},
        {"active_order_flow": [{"symbol": "BTCUSD", "confidence": 0.99, "side": "BUY"}]},
        {"ready_venue_count": 4, "venue_count": 4, "runtime_clearances": []},
        {"enabled": True, "self_measurement": {"agent_average_score": 0.99}},
        persist=False,
    )

    assert proof["status"] == "no_data"
    assert proof["auris_nodes"]["evaluated"] is False
    assert proof["master_formula"]["evaluated"] is False
    assert proof["operating_cycle"]["decision_output"]["action_state"] == "denied_no_fresh_provider_data"


def test_direct_route_denies_dry_run_before_any_provider_call():
    class OrderStub:
        def place_market_order(self, *_args, **_kwargs):
            raise AssertionError("dry-run route must not call the provider")

    trader = _trader()
    trader.dry_run = True
    trader.kraken = SimpleNamespace(client=OrderStub())

    result = trader._execute_kraken_spot_route("BUY", "XBTUSD", 65.0)

    assert result["status"] == "denied"
    assert result["submitted"] is False


@pytest.mark.parametrize(
    "method_name",
    [
        "_execute_kraken_spot_route",
        "_execute_alpaca_spot_route",
        "_execute_binance_spot_route",
        "_execute_kraken_margin_route",
        "_execute_binance_margin_route",
    ],
)
def test_every_direct_route_rejects_nonfinite_size_before_provider_call(method_name):
    trader = _trader()
    trader._runtime_real_orders_allowed = lambda: True
    trader._fresh_route_price_receipt = lambda *_args, **_kwargs: pytest.fail(
        "malformed order request must not probe a provider"
    )

    result = getattr(trader, method_name)("BUY", "BTCUSD", float("nan"))

    assert result["status"] == "no_data"
    assert result["submitted"] is False
    assert result["reason"] == "route_quote_value_missing_or_malformed"


def test_route_request_rejects_missing_symbol_and_invalid_side():
    trader = _trader()

    assert trader._validated_route_order_request("HOLD", "BTCUSD", 10.0)["reason"] == "route_side_missing_or_invalid"
    assert trader._validated_route_order_request("BUY", "", 10.0)["reason"] == "route_symbol_missing"


def test_dry_run_shadow_report_never_reads_or_mutates_shared_shadow_ledger():
    trader = _trader()
    trader.dry_run = True
    trader._read_shadow_trade_state = lambda: pytest.fail("dry run must not read shared shadow state")
    trader._persist_shadow_trade_report = lambda _report: pytest.fail("dry run must not persist shadow state")

    report = trader._build_shadow_trade_report(
        {"active_order_flow": []},
        {"runtime_clearances": []},
        persist=True,
    )

    assert report["mode"] == "shadow_validation_dry_run_non_persistent"
    assert report["persistent"] is False


def test_missing_fresh_quote_denies_order_call():
    class OrderStub:
        def place_market_order(self, *_args, **_kwargs):
            raise AssertionError("order must not be called without fresh price evidence")

    trader = _trader()
    trader.kraken = SimpleNamespace(client=OrderStub())
    trader._runtime_real_orders_allowed = lambda: True
    trader._fresh_route_price_receipt = lambda _venue, _symbol: {
        "status": "no_data",
        "data_status": "no_data",
        "reason": "stale_provider_timestamp",
    }

    result = trader._execute_kraken_spot_route("BUY", "XBTUSD", 65.0)

    assert result["status"] == "no_data"
    assert result["submitted"] is False
    assert result["reason"] == "stale_provider_timestamp"


def test_provider_submission_exception_is_pending_reconciliation_not_failure_or_fill():
    class AlpacaStub:
        def place_market_order(self, *_args, **_kwargs):
            raise TimeoutError("provider response lost")

    trader = _trader()
    trader.alpaca = AlpacaStub()
    trader._runtime_real_orders_allowed = lambda: True
    trader._fresh_route_price_receipt = lambda _venue, _symbol: {
        "status": "live",
        "data_status": "live",
        "price": 100.0,
    }

    result = trader._execute_alpaca_spot_route("BUY", "BTCUSD", 25.0)

    assert result["ok"] is False
    assert result["submitted"] is False
    assert result["status"] == "pending_reconciliation"
    assert result["reconciliation_required"] is True
    assert result["submission_state_unknown"] is True


def test_missing_account_receipt_blocks_spot_buy_posture():
    trader = _trader()
    trader.kraken = SimpleNamespace(client=object())
    trader._kraken_spot_portfolio_posture_cache = {}
    trader._kraken_spot_portfolio_posture_at = 0.0

    posture = trader._kraken_spot_portfolio_posture(force=True)

    assert posture["status"] == "no_data"
    assert posture["spot_buy_allowed"] is False


def test_malformed_account_receipt_fails_closed_without_balance_relabelling():
    trader = _trader()
    trader.kraken = SimpleNamespace(client=SimpleNamespace(get_account_balance=lambda: ["not", "a", "mapping"]))
    trader._kraken_spot_portfolio_posture_cache = {}
    trader._kraken_spot_portfolio_posture_at = 0.0

    posture = trader._kraken_spot_portfolio_posture(force=True)

    assert posture["status"] == "no_data"
    assert posture["spot_buy_allowed"] is False
    assert posture["reason"] == "malformed_provider_receipt"


def test_quote_usd_value_requires_fresh_market_receipt_for_every_non_usd_asset():
    trader = _trader()
    client = SimpleNamespace(
        convert_to_quote=lambda *_args, **_kwargs: pytest.fail("unstamped scalar conversion must not be used")
    )
    trader._fresh_route_price_receipt = lambda _venue, _symbol: {
        "status": "no_data",
        "data_status": "no_data",
        "reason": "provider_receipt_unavailable",
    }

    assert trader._kraken_quote_usd_value(client, "USD", 10.0) == 10.0
    assert trader._kraken_quote_usd_value(client, "USDT", 10.0) == 0.0
    assert trader._kraken_quote_usd_value(client, "GBP", 10.0) == 0.0

    trader._fresh_route_price_receipt = lambda _venue, symbol: {
        "status": "live",
        "data_status": "live",
        "price": 1.4 if symbol == "GBPUSD" else 1.0,
    }
    assert trader._kraken_quote_usd_value(client, "GBP", 10.0) == 14.0


def test_quote_options_reject_stale_account_cache_and_never_probe_unreceipted_free_balance():
    trader = _trader()
    trader._api_governor._cache["kraken:spot-account-balance"] = {
        "at": time.time() - trader_module.KRAKEN_SPOT_POSTURE_CACHE_TTL_SEC - 1.0,
        "value": {"ZUSD": "500"},
    }
    client = SimpleNamespace(
        get_account_balance=lambda: (_ for _ in ()).throw(OSError("provider unavailable")),
        get_free_balance=lambda *_args: pytest.fail("unreceipted scalar balance must not be used"),
    )

    assert trader._kraken_spot_quote_options(client) == []


def test_dynamic_budget_account_values_require_fresh_receipt_and_explicit_usd_denomination():
    trader = _trader()

    assert trader._quote_asset_usd_multiplier("USD") == 1.0
    assert trader._quote_asset_usd_multiplier("USDT") == 0.0
    assert trader._quote_asset_usd_multiplier("GBP") == 0.0

    unstamped = trader._balance_snapshot_values(
        {"cash_usd": 500.0, "equity_gbp": 1_000.0},
        default_currency="GBP",
    )
    assert unstamped["known"] is False
    assert unstamped["data_status"] == "no_data"

    fresh = trader._budgeted_client_balance_payload(
        "kraken",
        SimpleNamespace(get_account_balance=lambda: {"USD": "500", "GBP": "1000", "USDT": "1000"}),
    )
    values = trader._balance_snapshot_values(fresh)

    assert values["known"] is True
    assert values["deployable_cash_usd"] == 500.0
    assert values["data_status"] == "live"


def test_binance_budget_connectivity_requires_explicit_live_diagnostic():
    trader = _trader()
    trader.binance = object()
    trader._binance_diag = {}

    assert trader._exchange_connected_for_budget("binance") is False
    trader._binance_diag = {"network_ok": True}
    assert trader._exchange_connected_for_budget("binance") is True


def test_sell_quantity_requires_fresh_finite_provider_balance_receipt():
    trader = _trader()
    missing = SimpleNamespace(get_free_balance=lambda _asset: "nan")
    live = SimpleNamespace(get_free_balance=lambda asset: "2" if asset == "BTC" else None)

    assert trader._spot_sell_quantity(missing, "kraken", "BTCUSD", 100.0, 50.0) == 0.0
    assert trader._spot_sell_quantity(live, "kraken", "BTCUSD", 100.0, 50.0) == pytest.approx(1.998)


def test_waveform_observations_require_real_source_timestamp():
    trader = _trader()
    trader._central_beat_history = []
    normalized = {"BTCUSD": {"reference_price": 100.0, "volume_24h": 50.0}}
    unstamped = [{"source": "provider", "symbols": {"BTCUSD": {"price": 100.0, "volume_24h": 50.0}}}]

    assert trader._historical_waveform_live_observations(normalized, unstamped) == []

    observed = time.time() - 1.0
    stamped = [
        {
            "source": "provider",
            "symbols": {
                "BTCUSD": {
                    "price": 100.0,
                    "volume_24h": 50.0,
                    "source_timestamp": observed,
                    "timestamp_kind": "provider_event",
                }
            },
        }
    ]
    observations = trader._historical_waveform_live_observations(normalized, stamped)

    assert len(observations) == 1
    assert observations[0]["ts_ms"] == int(observed * 1000)


def test_world_macro_and_news_require_fresh_timestamped_provider_evidence():
    trader = _trader()
    trader._market_harp = SimpleNamespace(
        active_pluck_count=0,
        active_ripple_count=0,
        tick=lambda _prices: {},
        status_lines=lambda: [],
        cross_class_summary=lambda: [],
    )
    trader._cross_asset_correlator = SimpleNamespace(
        get_category_moves=lambda _changes: {},
        get_regime=lambda _changes: "NEUTRAL",
    )
    trader._publish_world_ecosystem_intelligence = lambda _report: None
    trader._load_world_macro_snapshot = lambda: {"risk_on_off": "RISK_ON"}
    trader._load_world_news_signal = lambda: {
        "sentiment": 0.9,
        "fetched_at": datetime.fromtimestamp(time.time() + 60.0).isoformat(),
    }

    blocked = trader._build_world_ecosystem_intelligence({}, [], {})

    assert blocked["macro_snapshot"]["usable_for_decision"] is False
    assert blocked["news_signal"]["usable_for_decision"] is False

    now_iso = datetime.now().isoformat()
    trader._load_world_macro_snapshot = lambda: {"risk_on_off": "RISK_ON", "generated_at": now_iso}
    trader._load_world_news_signal = lambda: {"sentiment": 0.9, "fetched_at": now_iso}
    live = trader._build_world_ecosystem_intelligence({}, [], {})

    assert live["macro_snapshot"]["usable_for_decision"] is True
    assert live["news_signal"]["usable_for_decision"] is True


def test_future_dated_live_posture_cache_is_not_reused():
    trader = _trader()
    trader.kraken = SimpleNamespace(client=object())
    trader._kraken_spot_portfolio_posture_cache = {"status": "live", "spot_buy_allowed": True}
    trader._kraken_spot_portfolio_posture_at = time.time() + 120.0

    posture = trader._kraken_spot_portfolio_posture(force=False)

    assert posture["status"] == "no_data"
    assert posture["spot_buy_allowed"] is False


def test_scanner_fusion_does_not_invent_timestamp_or_freshness():
    trader = _trader()
    trader._capability_present = lambda _path: True
    rows = trader._scanner_fusion_system_rows(
        central_beat={"source_count": 1},
        ranked=[{"symbol": "BTCUSD", "fast_money_profile": {"volatility_pct": 2.0}}],
        fast_money_intelligence={"candidate_count": 1, "orderbook_probe_count": 1},
        intelligence_mesh={"selection_mesh_score": 0.9},
    )

    assert rows
    assert all(row["last_timestamp"] is None for row in rows)
    assert all(row["fresh"] is False and row["usable_for_decision"] is False for row in rows)
    assert all(row["blocker"] == "central_beat_timestamp_missing_stale_or_future" for row in rows)


def test_deadman_submission_requires_provider_order_identity(monkeypatch):
    trader = _trader()
    trader._runtime_real_orders_allowed = lambda: True
    monkeypatch.setattr(trader_module, "KRAKEN_SPOT_DEADMAN_SWITCH_ENABLED", True)
    client = SimpleNamespace(
        place_trailing_stop_order=lambda *_args, **_kwargs: {"status": "accepted"},
    )

    result = trader._arm_kraken_spot_deadman_switch(
        client,
        {"symbol": "XBTUSD", "quantity": 1.0},
        {"symbol": "XBTUSD", "current_price": 100.0},
    )

    assert result["ok"] is False
    assert result["submitted"] is False
    assert result["status"] == "no_data"
    assert result["reason"] == "provider_submission_identity_missing"


def test_learning_rejects_unverified_trade_and_accepts_reconciled_fill(monkeypatch):
    trader = _trader()
    writes = []
    trader.get_runtime_health = lambda: {"status": "test"}
    trader._mycelium = SimpleNamespace(
        record_trade_profit=lambda **kwargs: writes.append(("mycelium", kwargs))
    )
    evidence_module = SimpleNamespace(
        append_trade_evidence=lambda *args, **kwargs: writes.append(("evidence", args, kwargs))
    )
    monkeypatch.setitem(sys.modules, "aureon.autonomous.aureon_cognitive_trade_evidence", evidence_module)

    assert trader._record_trade_profit({"net_pnl": 999.0, "eligible_for_learning": True}) is False
    assert writes == []

    fill = trader._confirmed_fill_receipt(_complete_fill())
    trade = {
        "eligible_for_learning": True,
        "fill_receipt": fill,
        "realized_entry_value_usd": 18.0,
        "realized_entry_fee_usd": 0.01,
        "net_pnl": 1.97,
    }
    assert trader._record_trade_profit(trade) is True
    assert [item[0] for item in writes] == ["evidence", "mycelium"]


def test_submission_acknowledgement_does_not_create_spot_position_or_mutate_state():
    trader = _trader()
    trader._load_kraken_spot_fast_profit_state = lambda: pytest.fail("submission must not load position state")
    trader._save_kraken_spot_fast_profit_state = lambda _state: pytest.fail("submission must not save position state")

    position = trader._record_kraken_spot_buy_position(
        symbol="XBTUSD",
        quote_usd=65.0,
        price=10.0,
        result={"order_id": "K-SUBMIT-1", "submitted": True, "status": "pending_reconciliation"},
        cost_profile={},
    )

    assert position == {}


def test_live_route_reports_submission_as_pending_without_opening_position():
    class OrderStub:
        def place_market_order(self, _symbol, _side, **_kwargs):
            return {
                "order_id": "K-SUBMIT-2",
                "submitted": True,
                "status": "pending_reconciliation",
                "data_status": "pending_reconciliation",
                "generated_values": False,
            }

    trader = _trader()
    trader.kraken = SimpleNamespace(client=OrderStub())
    trader._runtime_real_orders_allowed = lambda: True
    trader._fresh_route_price_receipt = lambda _venue, _symbol: {
        "status": "live",
        "data_status": "live",
        "price": 100.0,
    }
    trader._kraken_spot_portfolio_posture = lambda force=False: {
        "status": "live",
        "spot_buy_allowed": True,
    }
    trader._kraken_spot_quote_options = lambda _client: [
        {"asset": "USD", "available_usd": 500.0, "usd_per_quote": 1.0}
    ]
    trader._record_kraken_spot_buy_position = lambda **_kwargs: pytest.fail(
        "submission acknowledgement must not open a position"
    )

    result = trader._execute_kraken_spot_route("BUY", "XBTUSD", 65.0)

    assert result["ok"] is True
    assert result["submitted"] is True
    assert result["status"] == "pending_reconciliation"
    assert result["fill_confirmed"] is False
    assert result["fast_profit_position"] == {}


def test_terminal_fill_uses_observed_values_and_provider_time_for_position():
    trader = _trader()
    observed = time.time() - 1.0
    state = {"open_positions": [], "closed_positions": [], "last_check": {}}
    saved = {}
    trader._load_kraken_spot_fast_profit_state = lambda: state
    trader._save_kraken_spot_fast_profit_state = lambda payload: saved.update(payload)

    position = trader._record_kraken_spot_buy_position(
        symbol="XBTUSD",
        quote_usd=999.0,
        price=999.0,
        result=_complete_fill(observed),
        cost_profile={"estimated_entry_fee_usd": 999.0},
    )

    assert position["quantity"] == 2.0
    assert position["entry_price"] == 10.0
    assert position["entry_value_usd"] == 20.0
    assert position["entry_fee_usd"] == 0.02
    assert position["opened_at_epoch"] == pytest.approx(observed, abs=1e-5)
    assert saved["open_positions"][0]["source_order_id"] == "K-FILL-1"


def test_missing_exit_quote_keeps_position_and_makes_no_order_or_learning_call():
    class OrderStub:
        def place_market_order(self, *_args, **_kwargs):
            raise AssertionError("sell must not be called without fresh exit evidence")

    trader = _trader()
    trader.kraken = SimpleNamespace(client=OrderStub())
    trader._runtime_real_orders_allowed = lambda: True
    position = {
        "id": "P-1",
        "symbol": "XBTUSD",
        "quantity": 1.0,
        "entry_value_usd": 100.0,
        "entry_fee_usd": 0.1,
        "opened_at_epoch": time.time() - 60.0,
        "status": "open",
    }
    state = {"open_positions": [dict(position)], "closed_positions": [], "last_check": {}}
    saved = {}
    trader._load_kraken_spot_fast_profit_state = lambda: state
    trader._sync_kraken_spot_inventory_positions = lambda _client, payload: payload
    trader._kraken_spot_exit_price_receipt = lambda _client, _symbol: {
        "status": "no_data",
        "data_status": "no_data",
        "reason": "stale_provider_timestamp",
    }
    trader._save_kraken_spot_fast_profit_state = lambda payload: saved.update(payload)
    trader._publish_thought = lambda *_args, **_kwargs: pytest.fail("no close event may be published")
    trader._record_trade_profit = lambda *_args, **_kwargs: pytest.fail("no learning may occur")

    closed = trader._monitor_kraken_spot_fast_profit()

    assert closed == []
    assert saved["open_positions"] == [position]
    assert saved["closed_positions"] == []
    assert saved["last_check"]["checks"][0]["status"] == "no_data"


def test_monitor_uses_terminal_fill_values_for_realized_pnl_and_learning():
    observed = time.time()
    exit_fill = {
        **_complete_fill(observed),
        "order_id": "K-EXIT-1",
        "filled_qty": "0.999",
        "filled_avg_price": "102",
        "filled_notional": "101.898",
        "fee": "0.10",
    }

    class OrderStub:
        def place_market_order(self, _symbol, _side, **_kwargs):
            return dict(exit_fill)

    trader = _trader()
    trader.kraken = SimpleNamespace(client=OrderStub())
    trader._runtime_real_orders_allowed = lambda: True
    position = {
        "id": "P-REAL-1",
        "symbol": "XBTUSD",
        "quantity": 1.0,
        "entry_price": 100.0,
        "entry_value_usd": 100.0,
        "entry_fee_usd": 0.10,
        "opened_at_epoch": time.time() - 600.0,
        "status": "open",
    }
    state = {"open_positions": [dict(position)], "closed_positions": [], "last_check": {}}
    saved = {}
    learned = []
    trader._load_kraken_spot_fast_profit_state = lambda: state
    trader._sync_kraken_spot_inventory_positions = lambda _client, payload: payload
    trader._kraken_spot_exit_price_receipt = lambda _client, _symbol: {
        "status": "live",
        "data_status": "live",
        "price": 102.0,
        "provider_timestamp": observed,
    }
    trader._save_kraken_spot_fast_profit_state = lambda payload: saved.update(payload)
    trader._publish_thought = lambda *_args, **_kwargs: None
    trader._record_trade_profit = lambda trade: learned.append(trade)
    trader._arm_kraken_spot_deadman_switch = lambda *_args, **_kwargs: pytest.fail(
        "confirmed fill must not arm a second protection order"
    )

    closed = trader._monitor_kraken_spot_fast_profit()

    assert len(closed) == 1
    assert closed[0]["exit_price"] == 102.0
    assert closed[0]["exit_quantity"] == 0.999
    assert closed[0]["net_pnl"] == pytest.approx(1.7981)
    assert closed[0]["realized_entry_value_usd"] == pytest.approx(99.9)
    assert closed[0]["fill_receipt_complete"] is True
    assert closed[0]["eligible_for_learning"] is True
    assert learned == closed
    assert saved["open_positions"][0]["quantity"] == pytest.approx(0.001)
