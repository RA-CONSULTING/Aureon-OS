"""Orca kill chain real-fill ledger. Mocked responses only: no network, no orders.

``aureon_owned_qty`` counts a row only when the exchange status is FILLED,
PARTIALLY_FILLED, or Kraken closed, and only for that response's filled
quantity. Every other status counts as zero. A missing, unreadable, corrupt,
or partially written ledger is zero and does not raise.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal

import pytest

from aureon.exchanges import orca_real_fills as fills
from aureon_radar.bots import orca_unified_kill_chain as kc

FILLED_QTY = "0.02"
ORDER_ID = "884221"


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    ledger = tmp_path / "state" / "aureon_real_fills.jsonl"
    monkeypatch.setattr(fills, "LEDGER_PATH", ledger)
    monkeypatch.setattr(kc.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.chdir(tmp_path)
    return ledger


def _chain():
    chain = kc.UnifiedKillChain.__new__(kc.UnifiedKillChain)
    chain.wins_executed = []
    chain.real_portfolio = None
    chain.kraken = None
    chain.binance = None
    return chain


class _Binance:
    dry_run = False

    def __init__(self, response):
        self.response = response
        self.orders = []

    def get_free_balance(self, _asset):
        return 100.0

    def place_market_order(self, symbol, side, qty):
        self.orders.append((symbol, side, Decimal(str(qty))))
        return self.response


class _Kraken:
    last_balance_source = "live"

    def __init__(self, response=None, dry_run=False):
        self.response = response
        self.dry_run = dry_run
        self.orders = []

    def get_account_balance(self):
        return {"ZUSD": 100.0}

    def get_balance(self):
        return {"USD": 100.0}

    def place_market_order(self, symbol, side, qty):
        self.orders.append((symbol, side, Decimal(str(qty))))
        return self.response


def _response(**overrides):
    payload = {
        "status": "FILLED",
        "orderId": ORDER_ID,
        "executedQty": FILLED_QTY,
        "requestedQty": "0.1",
        "origQty": "0.1",
        "avgPrice": "100",
        "clientOrderId": "ck-884221",
        "side": "BUY",
    }
    payload.update(overrides)
    return payload


def _rows(ledger):
    if not ledger.exists():
        return []
    return [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_confirmed_fill_records_exchange_qty_not_the_request(isolated):
    client = _Binance(_response())
    chain = _chain()
    chain.binance = client
    # Existing sizing buys 10% of the 100 USDT balance at price 100, so the
    # request is 0.1. The exchange filled 0.02.
    result = chain._execute_trade({"exchange": "binance", "symbol": "ETHUSDT", "price": 100})

    assert result["status"] == "FILLED"
    assert client.orders[0][2] == Decimal("0.1")
    rows = _rows(isolated)
    assert len(rows) == 1
    assert rows[0]["filled_qty"] == FILLED_QTY
    assert rows[0]["executedQty"] == FILLED_QTY
    assert Decimal(rows[0]["filled_qty"]) != client.orders[0][2]
    assert rows[0]["venue"] == "binance"
    assert rows[0]["symbol"] == "ETHUSDT"
    assert rows[0]["side"] == "BUY"
    assert rows[0]["status"] == "FILLED"
    assert rows[0]["exchange_order_id"] == ORDER_ID
    assert rows[0]["client_order_id"] == "ck-884221"
    assert rows[0]["source"] == "orca_kill_chain"
    assert rows[0]["avg_price"] == "100"
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(FILLED_QTY)

    chain._execute_trade({"exchange": "binance", "symbol": "ETHUSDT", "price": 100})
    assert len(_rows(isolated)) == 1
    assert fills.aureon_owned_qty("binance", "ethusdt") == Decimal(FILLED_QTY)


def test_partial_fill_records_partial_qty(isolated):
    client = _Binance(_response(status="PARTIALLY_FILLED", orderId="884222"))
    chain = _chain()
    chain.binance = client
    result = chain._execute_trade({"exchange": "binance", "symbol": "ETHUSDT", "price": 100})

    assert result["status"] == "FAILED"
    assert client.orders[0][2] == Decimal("0.1")
    rows = _rows(isolated)
    assert len(rows) == 1
    assert rows[0]["status"] == "PARTIALLY_FILLED"
    assert rows[0]["filled_qty"] == FILLED_QTY
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(FILLED_QTY)


@pytest.mark.parametrize(
    "response",
    [
        _response(status="REJECTED", orderId="884223"),
        _response(status="FILLED", orderId="884224", executedQty="0"),
        _response(status="FILLED", orderId="884225", executedQty="0", filled_qty="0"),
        _response(status="FILLED", orderId=None),
        _response(status="FILLED", orderId="0"),
        _response(truth_status="simulated", mode="shadow"),
        _response(status="not_submitted", dryRun=True, submitted=False, executedQty=None, orderId=None),
    ],
)
def test_rejected_zero_dry_run_and_shadow_write_nothing(isolated, response):
    client = _Binance(response)
    chain = _chain()
    chain.binance = client
    chain._execute_trade({"exchange": "binance", "symbol": "ETHUSDT", "price": 100})

    assert not isolated.exists()
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(0)
    assert client.orders


def test_kraken_dry_run_not_submitted_receipt_contributes_zero(isolated):
    receipt = {
        "provider": "kraken",
        "venue": "kraken",
        "orderId": None,
        "symbol": "ETHUSD",
        "side": "BUY",
        "requestedQty": "0.1",
        "origQty": "0.1",
        "executedQty": None,
        "filled_qty": None,
        "status": "not_submitted",
        "data_status": "not_submitted",
        "truth_status": "not_submitted",
        "submitted": False,
        "dryRun": True,
        "reason": "dry_run_order_not_submitted",
        "fill_receipt_complete": False,
    }
    client = _Kraken(receipt, dry_run=False)
    chain = _chain()
    chain.kraken = client
    result = chain._execute_trade({"exchange": "kraken", "symbol": "ETHUSD", "price": 100})

    assert result["status"] == "FILLED"  # attempt log still treats a non-error body as filled
    assert client.orders
    assert not isolated.exists()
    assert fills.aureon_owned_qty("kraken", "ETHUSD") == Decimal(0)

    isolated.parent.mkdir(parents=True, exist_ok=True)
    isolated.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    assert fills.aureon_owned_qty("kraken", "ETHUSD") == Decimal(0)


def test_kraken_client_dry_run_writes_nothing(isolated):
    client = _Kraken(_response(), dry_run=True)
    chain = _chain()
    chain.kraken = client
    result = chain._execute_trade({"exchange": "kraken", "symbol": "ETHUSD", "price": 100})

    assert result["status"] == "BALANCE_DRY_RUN"
    assert client.orders == []
    assert not isolated.exists()
    assert fills.aureon_owned_qty("kraken", "ETHUSD") == Decimal(0)


def test_owned_qty_is_buys_minus_sells_and_same_order_is_not_double_counted(isolated):
    buy = _response(orderId="884221", side="BUY")
    second = _response(orderId="884222", side="BUY")
    sell = _response(orderId="884223", side="SELL", status="FILLED")
    assert fills.record_confirmed_fill("binance", "ETHUSDT", "BUY", buy) is not None
    assert fills.record_confirmed_fill("binance", "ETHUSDT", "BUY", second) is not None
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal("0.04")
    assert fills.record_confirmed_fill("binance", "ETHUSDT", "SELL", sell) is not None
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(FILLED_QTY)
    assert fills.record_confirmed_fill("binance", "ETHUSDT", "BUY", buy)["exchange_order_id"] == "884221"
    assert len(_rows(isolated)) == 3

    closed = _response(status="closed", orderId="884226", side="BUY", symbol="XETHZUSD")
    assert fills.record_confirmed_fill("kraken", "ETHUSD", "buy", closed) is not None
    assert fills.aureon_owned_qty("kraken", "ETHUSD") == Decimal(FILLED_QTY)
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(FILLED_QTY)


def test_other_statuses_contribute_zero_even_with_a_quantity(isolated):
    isolated.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, status in enumerate(
        ("ERROR", "NO_FUNDS", "BUY_FAILED", "ARBITRAGE_LOGGED", "PENDING_RECONCILIATION", "NOT_SUBMITTED"),
        start=1,
    ):
        rows.append({
            "venue": "binance",
            "symbol": "ETHUSDT",
            "side": "BUY",
            "status": status,
            "filled_qty": FILLED_QTY,
            "executedQty": FILLED_QTY,
            "exchange_order_id": f"88430{index}",
            "source": "orca_kill_chain",
        })
    rows.append({
        "venue": "binance",
        "symbol": "ETHUSDT",
        "side": "BUY",
        "status": "FILLED",
        "filled_qty": FILLED_QTY,
        "executedQty": FILLED_QTY,
        "exchange_order_id": ORDER_ID,
        "source": "orca_kill_chain",
    })
    isolated.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(FILLED_QTY)


def test_completed_arbitrage_records_each_leg_on_its_venue(isolated):
    buy = _response(orderId="K-884221", side="BUY", executedQty=FILLED_QTY, clientOrderId="ck-kraken-884221")
    sell = _response(orderId="B-884221", side="SELL", executedQty=FILLED_QTY, clientOrderId="ck-binance-884221")
    kraken = _Kraken(buy)
    binance = _Binance(sell)
    chain = _chain()
    chain.kraken = kraken
    chain.binance = binance
    result = chain._execute_trade({
        "exchange": "arbitrage",
        "symbol": "ETH/USD",
        "buy_exchange": "kraken",
        "sell_exchange": "binance",
        "kraken_price": 100,
        "binance_price": 100,
    })

    assert result["status"] == "ARBITRAGE_EXECUTED"
    assert kraken.orders == [("ETHUSD", "buy", Decimal("0.8"))]
    assert binance.orders == [("ETHUSDT", "SELL", Decimal(FILLED_QTY))]
    rows = _rows(isolated)
    assert [(row["venue"], row["symbol"], row["side"], row["filled_qty"]) for row in rows] == [
        ("kraken", "ETHUSD", "BUY", FILLED_QTY),
        ("binance", "ETHUSDT", "SELL", FILLED_QTY),
    ]
    assert fills.aureon_owned_qty("kraken", "ETHUSD") == Decimal(FILLED_QTY)
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == -Decimal(FILLED_QTY)
    assert (
        fills.aureon_owned_qty("kraken", "ETHUSD") + fills.aureon_owned_qty("binance", "ETHUSDT")
        == Decimal(0)
    )
    assert fills.aureon_owned_qty("kraken", "ETHUSDT") == Decimal(0)
    assert fills.aureon_owned_qty("binance", "ETHUSD") == Decimal(0)


def test_missing_ledger_is_zero_and_does_not_create_a_file(isolated):
    assert not isolated.exists()
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(0)
    assert fills.aureon_owned_qty("", "ETHUSDT") == Decimal(0)
    assert not isolated.exists()


def test_unreadable_ledger_is_zero(isolated):
    isolated.parent.mkdir(parents=True, exist_ok=True)
    isolated.mkdir()
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(0)


def test_corrupt_ledger_is_zero(isolated):
    isolated.parent.mkdir(parents=True, exist_ok=True)
    isolated.write_text("{not json\n", encoding="utf-8")
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(0)


def test_partially_written_ledger_is_zero_even_when_an_earlier_line_is_valid(isolated):
    isolated.parent.mkdir(parents=True, exist_ok=True)
    whole = {
        "venue": "binance",
        "symbol": "ETHUSDT",
        "side": "BUY",
        "status": "FILLED",
        "filled_qty": FILLED_QTY,
        "executedQty": FILLED_QTY,
        "exchange_order_id": ORDER_ID,
        "source": "orca_kill_chain",
    }
    torn = '{"status": "FILLED", "filled_qty": "0.02"'
    isolated.write_text(json.dumps(whole) + "\n" + torn, encoding="utf-8")
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(0)


def test_fill_write_failure_is_logged_and_does_not_raise(isolated, monkeypatch, caplog):
    isolated.parent.mkdir(parents=True, exist_ok=True)
    blocker = isolated.parent / "not-a-directory"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(fills, "LEDGER_PATH", blocker / "aureon_real_fills.jsonl")
    client = _Binance(_response())
    chain = _chain()
    chain.binance = client
    with caplog.at_level(logging.ERROR, logger="aureon.orca_real_fills"):
        result = chain._execute_trade({"exchange": "binance", "symbol": "ETHUSDT", "price": 100})

    assert result["status"] == "FILLED"
    assert "real fill not recorded" in caplog.text
    assert ORDER_ID in caplog.text
    assert FILLED_QTY in caplog.text
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(0)


def test_attempt_log_write_failure_is_logged(isolated, monkeypatch, capsys):
    real_open = open

    def guarded(file, *args, **kwargs):
        if str(file) == "orca_executions.json":
            raise OSError("disk full")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", guarded)
    client = _Binance(_response())
    chain = _chain()
    chain.binance = client
    result = chain._execute_trade({"exchange": "binance", "symbol": "ETHUSDT", "price": 100})

    assert result["status"] == "FILLED"
    output = capsys.readouterr().out
    assert "orca_executions.json write failed" in output
    assert "OSError" in output
    assert "disk full" in output
    rows = _rows(isolated)
    assert len(rows) == 1
    assert rows[0]["filled_qty"] == FILLED_QTY
