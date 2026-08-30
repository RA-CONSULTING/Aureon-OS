import sys
import time


_host_platform = sys.platform
try:
    # Several optional legacy subsystems wrap sys.stdout when they see win32.
    # The Gaia unit boundary does not need that terminal behavior.
    if _host_platform == "win32":
        sys.platform = "test-no-terminal-wrapper"
    from aureon.bots.gaia_planetary_reclaimer import (
        PlanetaryReclaimer,
        _binance_market_receipt,
    )
finally:
    sys.platform = _host_platform


class _Queen:
    def __init__(self):
        self.records = []

    def record_trade(self, *args, **kwargs):
        self.records.append((args, kwargs))

    def validate_portfolio_growth(self):
        return {"validated": False, "growing": False}


def _bare_reclaimer():
    reclaimer = object.__new__(PlanetaryReclaimer)
    reclaimer.no_data_events = []
    reclaimer.verified_trades = []
    reclaimer.platform_stats = {
        name: {"trades": 0, "profit": 0.0, "verified": 0, "last_trade": None}
        for name in ("binance", "alpaca", "kraken")
    }
    reclaimer.profit = 0.0
    reclaimer.trades = 0
    reclaimer.entries = {}
    reclaimer.queen = _Queen()
    reclaimer.mycelium = None
    reclaimer.log = lambda _message: None
    return reclaimer


def _complete_fill(now):
    return {
        "status": "filled",
        "source_id": "provider:order:abc",
        "source_timestamp": now,
        "truth_status": "real_observed",
        "generated_values": False,
        "fill_receipt_complete": True,
        "eligible_for_accounting": True,
        "eligible_for_learning": True,
        "provider_order_id": "abc",
        "filled_qty": "2",
        "filled_avg_price": "101",
        "filled_notional": "202",
        "fee": "0.25",
        "fee_currency": "USD",
        "realized_pnl": "1.75",
        "pnl_currency": "USD",
    }


def test_market_provenance_and_terminal_accounting_are_fail_closed():
    now = time.time()
    raw_ticker = {
        "symbol": "BTCUSDC",
        "lastPrice": "60000",
        "bidPrice": "59999",
        "askPrice": "60001",
        "priceChangePercent": "1.25",
        "volume": "12",
        "quoteVolume": "720000",
        "closeTime": int(now * 1000),
    }
    observation = _binance_market_receipt(raw_ticker, "BTCUSDC", now=now)
    assert observation is not None
    assert observation["generated_values"] is False
    assert observation["source_timestamp"] == raw_ticker["closeTime"]
    assert observation["spread"] > 0
    assert _binance_market_receipt(
        {**raw_ticker, "closeTime": int((now - 121) * 1000)}, "BTCUSDC", now=now
    ) is None
    assert _binance_market_receipt(
        {key: value for key, value in raw_ticker.items() if key != "volume"},
        "BTCUSDC",
        now=now,
    ) is None

    reclaimer = _bare_reclaimer()
    pending = {
        "status": "pending_reconciliation",
        "source_id": "provider:submission:abc",
        "source_timestamp": now,
        "truth_status": "real_observed",
        "generated_values": False,
        "fill_receipt_complete": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "provider_order_id": "abc",
    }
    assert reclaimer.record_verified_trade("alpaca", "BTC/USD", "SELL", pending) is False
    assert reclaimer.trades == 0
    assert reclaimer.profit == 0.0
    assert reclaimer.queen.records == []
    assert reclaimer.no_data_events[-1]["data_status"] == "no_data"

    assert reclaimer.record_verified_trade(
        "alpaca", "BTC/USD", "SELL", _complete_fill(now)
    ) is True
    assert reclaimer.platform_stats["alpaca"]["verified"] == 1
    assert reclaimer.platform_stats["alpaca"]["profit"] == 1.75
    assert reclaimer.trades == 1
    assert reclaimer.profit == 1.75
    assert reclaimer.verified_trades[0]["source_timestamp"] == now
    assert len(reclaimer.queen.records) == 1


def test_unstamped_account_receipts_never_reach_order_methods():
    class _NoOrderAlpaca:
        def get_account(self):
            return {"cash": "100"}

        def get_positions(self):
            raise AssertionError("positions must not be consumed after an unstamped account")

        def place_order(self, *_args, **_kwargs):
            raise AssertionError("order must not be submitted")

    class _NoOrderKraken:
        def account(self):
            return {"balances": [{"asset": "USD", "free": "100"}]}

        def place_market_order(self, *_args, **_kwargs):
            raise AssertionError("order must not be submitted")

    reclaimer = _bare_reclaimer()
    reclaimer.alpaca = _NoOrderAlpaca()
    reclaimer.alpaca_scan_and_trade()
    assert reclaimer.no_data_events[-1]["surface"] == "alpaca.account"

    reclaimer.kraken = _NoOrderKraken()
    reclaimer.kraken_scan_and_trade()
    assert reclaimer.no_data_events[-1]["surface"] == "kraken.account"
