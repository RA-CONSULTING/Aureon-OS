"""Focused offline regression tests for unified-ecosystem data provenance."""

from __future__ import annotations

import importlib
import io
import os
import time
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch


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
    ecosystem_module = importlib.import_module("aureon.trading.aureon_unified_ecosystem")


def market_row(now: float, **overrides):
    row = {
        "price": 100.0,
        "bid": 99.9,
        "ask": 100.1,
        "high": 105.0,
        "low": 95.0,
        "volume": 1_000.0,
        "change24h": 1.25,
        "truth_status": "live",
        "source_id": "provider:test:ticker",
        "source_timestamp": now,
        "received_at": now,
        "generated_values": False,
    }
    row.update(overrides)
    return row


class NoOrderClient:
    def __init__(self):
        self.order_calls = []

    def place_market_order(self, *args, **kwargs):
        self.order_calls.append((args, kwargs))
        raise AssertionError("provider order must not be called")

    def normalize_symbol(self, _exchange, symbol):
        return symbol


def test_market_evidence_rejects_missing_stale_and_future_provider_time():
    now = time.time()

    assert ecosystem_module._validate_market_evidence(market_row(now), now=now)[0] is True
    assert ecosystem_module._validate_market_evidence({"price": 100.0}, now=now)[0] is False
    assert ecosystem_module._validate_market_evidence(
        market_row(now - ecosystem_module.MARKET_DATA_MAX_AGE_SECONDS - 1), now=now
    )[0] is False
    assert ecosystem_module._validate_market_evidence(
        market_row(now + ecosystem_module.MARKET_DATA_FUTURE_SKEW_SECONDS + 1), now=now
    )[0] is False


def test_provider_ticker_normalizer_requires_complete_real_fields():
    now = time.time()
    field_map = {
        "price": ("lastPrice",),
        "high": ("highPrice",),
        "low": ("lowPrice",),
    }
    incomplete = {"lastPrice": "100", "highPrice": "101", "closeTime": int(now * 1000)}
    assert ecosystem_module._normalise_provider_ticker(
        incomplete, source_id="binance:ticker", field_map=field_map, received_at=now
    ) is None

    complete = {**incomplete, "lowPrice": "99"}
    normalized = ecosystem_module._normalise_provider_ticker(
        complete, source_id="binance:ticker", field_map=field_map, received_at=now
    )
    assert normalized is not None
    assert normalized["low"] == 99.0
    assert normalized["generated_values"] is False


def test_fill_receipt_separates_submission_from_quote_fee_complete_fill():
    now_ms = int(time.time() * 1000)
    submitted = ecosystem_module._provider_fill_receipt(
        "kraken", {"txid": ["K-1"], "status": "submitted"}
    )
    assert submitted["execution_status"] == "submitted"
    assert submitted["filled_price"] is None

    filled = ecosystem_module._provider_fill_receipt(
        "binance",
        {
            "symbol": "BTCUSDT",
            "orderId": "B-1",
            "status": "FILLED",
            "transactTime": now_ms,
            "fills": [
                {
                    "tradeId": "T-1",
                    "qty": "2",
                    "price": "10",
                    "commission": "0.02",
                    "commissionAsset": "USDT",
                }
            ],
        },
    )
    assert filled["execution_status"] == "filled"
    assert filled["filled_quote_value"] == 20.0
    assert filled["actual_fee"] == 0.02
    assert filled["actual_fee_asset"] == "USDT"

    non_quote_fee = ecosystem_module._provider_fill_receipt(
        "binance",
        {
            "symbol": "BTCUSDT",
            "orderId": "B-2",
            "status": "FILLED",
            "transactTime": now_ms,
            "fills": [
                {
                    "qty": "2",
                    "price": "10",
                    "commission": "0.01",
                    "commissionAsset": "BNB",
                }
            ],
        },
    )
    assert non_quote_fee["execution_status"] == "filled"
    assert non_quote_fee["actual_fee"] is None


def test_protective_cancel_requires_explicit_matching_acknowledgement():
    assert ecosystem_module._provider_cancel_acknowledged(True, "O-1") is True
    assert ecosystem_module._provider_cancel_acknowledged(
        {"status": "cancelled", "orderId": "O-1"}, "O-1"
    ) is True
    assert ecosystem_module._provider_cancel_acknowledged(None, "O-1") is False
    assert ecosystem_module._provider_cancel_acknowledged(
        {"status": "cancelled", "orderId": "OTHER"}, "O-1"
    ) is False


def test_unified_confirmation_withholds_provider_order_without_fresh_evidence():
    client = NoOrderClient()
    confirmation = ecosystem_module.UnifiedTradeConfirmation(client)

    missing = confirmation.submit_order("binance", "BTCUSDT", "BUY", quote_qty=10.0)
    stale = confirmation.submit_order(
        "binance",
        "BTCUSDT",
        "SELL",
        quantity=0.1,
        market_evidence=market_row(time.time() - 1_000),
    )

    assert missing["execution_status"] == "not_submitted"
    assert stale["execution_status"] == "not_submitted"
    assert client.order_calls == []


def test_kraken_txid_is_submission_not_fill():
    confirmation = ecosystem_module.UnifiedTradeConfirmation(NoOrderClient())
    parsed = confirmation.normalize_order_result(
        "kraken", "XBTUSD", "BUY", None, 10.0, {"txid": ["K-2"]}
    )

    assert parsed["status"] == "SUBMITTED"
    assert parsed["execution_status"] == "submitted"
    assert parsed["fill_receipt"]["filled_quantity"] is None


def test_router_skips_stale_quotes():
    class QuoteClient:
        def normalize_symbol(self, _exchange, symbol):
            return symbol

        def get_ticker(self, _exchange, _symbol):
            return market_row(time.time() - 1_000)

    router = ecosystem_module.SmartOrderRouter(QuoteClient())
    assert router.get_best_quote("BTCUSDT", "BUY") is None


def test_router_and_arbitrage_require_fresh_account_receipts_before_orders():
    class FreshQuoteClient(NoOrderClient):
        def get_ticker(self, _exchange, _symbol):
            return market_row(time.time())

    client = FreshQuoteClient()
    router = ecosystem_module.SmartOrderRouter(client)
    routed = router.route_order("BTCUSDT", "BUY", quote_qty=10.0)
    assert routed["execution_status"] == "not_submitted"

    scanner = ecosystem_module.CrossExchangeArbitrageScanner(client)
    opportunity = {
        "symbol": "BTCUSD",
        "buy_exchange": "binance",
        "sell_exchange": "kraken",
        "buy_price": 100.0,
        "sell_price": 101.0,
        "price": 100.0,
        "truth_status": "real_derived",
        "source_id": "provider:binance+provider:kraken",
        "source_timestamp": time.time(),
        "received_at": time.time(),
        "generated_values": False,
    }
    arbitrage = scanner.execute_arbitrage(opportunity, amount_usd=10.0)
    assert arbitrage["execution_status"] == "not_submitted"
    assert client.order_calls == []


def test_rebalance_dry_run_never_calls_provider_or_claims_fill():
    client = NoOrderClient()
    rebalancer = ecosystem_module.PortfolioRebalancer(client)
    rebalancer.calculate_rebalance_trades = lambda: [
        {"asset": "BTC", "action": "BUY", "amount_usd": 10.0, "exchange": "binance"}
    ]

    result = rebalancer.execute_rebalance(dry_run=True)

    assert result["success"] is False
    assert result["trades_executed"] == 0
    assert result["orders_submitted"] == 0
    assert result["execution_status"] == "not_submitted"
    assert result["trades"][0]["result"]["provider_order_id"] is None
    assert client.order_calls == []


def test_underfunded_quote_liquidity_denies_without_conversion_order():
    exchange_client = type("Exchange", (), {"get_balance": lambda self, _asset: 2.0})()
    client = NoOrderClient()
    client.clients = {"binance": exchange_client}
    ecosystem = object.__new__(ecosystem_module.AureonKrakenEcosystem)
    ecosystem.client = client
    ecosystem.dry_run = False
    ecosystem._liquidity_warnings = set()

    ok, available, reason = ecosystem.ensure_quote_liquidity("binance", "USDT", 10.0)

    assert ok is False
    assert available == 2.0
    assert "prefund" in reason
    assert client.order_calls == []


def test_incomplete_account_conversion_makes_entire_equity_snapshot_no_data():
    class AccountClient:
        def get_all_balances(self):
            return {"binance": {"GBP": "5", "BTC": "1"}}

        def convert_to_quote(self, *_args):
            return None

    ecosystem = object.__new__(ecosystem_module.AureonKrakenEcosystem)
    ecosystem.client = AccountClient()

    total, cash, holdings = ecosystem.compute_total_equity()

    assert total is None
    assert cash is None
    assert holdings == {}
    assert ecosystem.account_truth_status == "no_data"
    assert "binance:BTC:conversion_unavailable" in ecosystem.account_evidence["incomplete_rows"]


def test_open_and_close_dry_runs_do_not_mutate_positions_or_call_provider():
    now = time.time()
    client = NoOrderClient()
    ecosystem = object.__new__(ecosystem_module.AureonKrakenEcosystem)
    ecosystem.client = client
    ecosystem.dry_run = True
    ecosystem.positions = {}
    ecosystem.ticker_cache = {}
    opportunity = market_row(
        now,
        symbol="BTCUSDT",
        quick_kill={
            "prob_quick_kill": 0.8,
            "confidence": 0.8,
            "estimated_seconds": 30.0,
            "truth_status": "real_derived",
            "source_id": "provider:test:quick-kill",
            "source_timestamp": now,
            "generated_values": False,
        },
    )

    stale_consensus = dict(opportunity)
    stale_consensus["quick_kill"] = {
        **opportunity["quick_kill"],
        "source_timestamp": now - 1_000,
    }
    denied = ecosystem.open_position(stale_consensus)
    assert denied["execution_status"] == "denied"
    assert ecosystem.positions == {}
    assert client.order_calls == []

    opened = ecosystem.open_position(opportunity)
    assert opened["execution_status"] == "not_submitted"
    assert opened["truth_status"] == "dry_run"
    assert ecosystem.positions == {}

    position = ecosystem_module.Position(
        symbol="BTCUSDT",
        entry_price=90.0,
        quantity=1.0,
        entry_fee=0.1,
        entry_value=90.0,
        momentum=1.0,
        coherence=0.9,
        entry_time=now - 60,
        dominant_node="Auris",
        exchange="binance",
        provider_order_id="ENTRY-1",
        fill_source_id="binance_order_fill",
        fill_source_timestamp=now - 60,
        truth_status="live",
    )
    ecosystem.positions = {"BTCUSDT": position}
    ecosystem.realtime_price_evidence = {"BTCUSDT": market_row(now)}
    ecosystem.realtime_prices = {"BTCUSDT": 100.0}

    closed = ecosystem.close_position("BTCUSDT", "TEST", 1.0, 100.0)
    assert closed["execution_status"] == "not_submitted"
    assert closed["truth_status"] == "dry_run"
    assert ecosystem.positions["BTCUSDT"] is position
    assert client.order_calls == []


def test_capital_tickers_and_empty_historical_ranking_never_invent_rows_or_call_provider():
    orchestrator = object.__new__(ecosystem_module.MultiExchangeOrchestrator)
    assert orchestrator._get_capital_tickers(object()) == {}

    class HistoricalClient:
        def __init__(self):
            self.calls = 0

        def get_24h_historical(self, **_kwargs):
            self.calls += 1
            raise AssertionError("historical provider must not be called without ranked evidence")

    historical_client = HistoricalClient()
    ecosystem = object.__new__(ecosystem_module.AureonKrakenEcosystem)
    ecosystem.client = type("Multi", (), {"binance": historical_client})()
    ecosystem.ticker_cache = {}
    ecosystem.price_history = {}

    ecosystem._bootstrap_24h_historical()
    assert historical_client.calls == 0
    assert ecosystem.price_history == {}
