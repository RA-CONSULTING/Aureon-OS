"""Orca kill chain real-fill ledger. Mocked responses only: no network, no orders.

``aureon_owned_qty`` counts a row only when the exchange status is FILLED,
PARTIALLY_FILLED, or Kraken closed, and only for that response's filled
quantity. Every other status counts as zero. A missing, unreadable, corrupt,
or partially written ledger is zero and does not raise.
"""

from __future__ import annotations

import json
import logging
import multiprocessing
from decimal import Decimal

import pytest

from aureon.exchanges import orca_real_fills as fills
from aureon_radar.bots import orca_unified_kill_chain as kc

FILLED_QTY = "0.02"
ORDER_ID = "884221"
KRAKEN_TXID = "OQCLML-BW3P3-BUCMWZ"


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    ledger = tmp_path / "state" / "aureon_real_fills.jsonl"
    monkeypatch.setattr(fills, "LEDGER_PATH", ledger)
    monkeypatch.setattr(kc.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fills.time, "sleep", lambda *_args, **_kwargs: None)
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

    def __init__(self, response=None, dry_run=False, queries=None, repeat=None):
        self.response = response
        self.dry_run = dry_run
        self.orders = []
        self.queries = list(queries or [])
        self.repeat = repeat
        self.queried = []

    def get_account_balance(self):
        return {"ZUSD": 100.0}

    def get_balance(self):
        return {"USD": 100.0}

    def place_market_order(self, symbol, side, qty):
        self.orders.append((symbol, side, Decimal(str(qty))))
        return self.response

    def get_order_status(self, order_id):
        self.queried.append(order_id)
        if self.queries:
            nxt = self.queries.pop(0)
            return nxt(order_id) if callable(nxt) else nxt
        if self.repeat is not None:
            return self.repeat
        return {"status": "open", "vol_exec": "0", "txid": order_id}


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


def _add_order_ack(txid=KRAKEN_TXID, **overrides):
    """Kraken place_market_order: AddOrder ack, not a fill."""
    payload = {
        "provider": "kraken",
        "venue": "kraken",
        "orderId": txid,
        "txid": [txid],
        "symbol": "ETHUSD",
        "side": "BUY",
        "requestedQty": "0.8",
        "origQty": "0.8",
        "executedQty": None,
        "filled_qty": None,
        "status": "pending_reconciliation",
        "data_status": "pending_reconciliation",
        "truth_status": "real_observed",
        "submitted": True,
        "dryRun": False,
        "reconciliation_required": True,
        "provider_receipt_type": "AddOrder",
        "reason": "terminal_provider_fill_receipt_required",
    }
    payload.update(overrides)
    return payload


def _query_closed(txid=KRAKEN_TXID, vol_exec=FILLED_QTY, **overrides):
    """Inner QueryOrders order: status closed, vol_exec is the fill."""
    payload = {
        "status": "closed",
        "vol": "0.8",
        "vol_exec": vol_exec,
        "cost": "2.0",
        "fee": "0.0052",
        "price": "100",
        "txid": txid,
        "descr": {"pair": "ETHUSD", "type": "buy", "ordertype": "market"},
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


def test_disagreeing_fill_quantities_are_not_a_fill():
    """executedQty 0.5 and filled_qty 1.0 do not agree, so the reading is None.

    Pins the check that every present fill-quantity field is the same value.
    Dropping that check would return the first field, 0.5.
    """
    payload = {"executedQty": "0.5", "filled_qty": "1.0"}
    assert fills._filled_qty(payload) is None
    assert fills.confirmed_fill_record("binance", "ETHUSDT", "BUY", _response(**payload)) is None


def test_a_single_nan_quantity_is_not_a_fill(isolated):
    """A lone NaN quantity is not a fill and records nothing.

    Two NaN fields fail the agree check because NaN != NaN. One vol_exec has
    no second field, so only the finite check can return None. Removing that
    check lets the closed reading through as Decimal('NaN').
    """
    assert fills._filled_qty({"executedQty": "NaN"}) is None
    assert (
        fills.confirmed_fill_record(
            "binance", "ETHUSDT", "BUY", _response(executedQty="NaN", orderId="884241")
        )
        is None
    )
    assert (
        fills.record_confirmed_fill(
            "binance", "ETHUSDT", "BUY", _response(executedQty="NaN", orderId="884241")
        )
        is None
    )

    closed = {"status": "closed", "vol_exec": "NaN", "txid": KRAKEN_TXID}
    assert fills._closed_query_fill(closed) is None
    assert fills.record_kraken_acknowledged_fill(object(), "ETHUSD", "buy", closed) is None

    assert not isolated.exists()
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(0)
    assert fills.aureon_owned_qty("kraken", "ETHUSD") == Decimal(0)


def test_a_zero_fill_quantity_rejects_the_other_fields():
    """executedQty 1 with filled_qty 0 is not a fill.

    Pins ``if qty is None: return None``. Continuing past the zero field would
    keep executedQty 1.
    """
    payload = {"executedQty": "1", "filled_qty": "0"}
    assert fills._filled_qty(payload) is None
    assert fills.confirmed_fill_record("binance", "ETHUSDT", "BUY", _response(**payload)) is None


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
    """Kraken answers with an AddOrder ack, then QueryOrders closed.

    The sell still waits on the ack's own status being FILLED, so this buy
    does not send the Binance sell. The ledger still takes vol_exec.
    """
    buy = _add_order_ack()
    closed = _query_closed()
    kraken = _Kraken(buy, queries=[closed])
    binance = _Binance(_response(orderId="B-884221", side="SELL", executedQty=FILLED_QTY))
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

    assert result["status"] == "BUY_FAILED"
    assert kraken.orders == [("ETHUSD", "buy", Decimal("0.8"))]
    assert kraken.queried == [KRAKEN_TXID]
    assert binance.orders == []
    rows = _rows(isolated)
    assert len(rows) == 1
    assert rows[0]["venue"] == "kraken"
    assert rows[0]["symbol"] == "ETHUSD"
    assert rows[0]["side"] == "BUY"
    assert rows[0]["status"] == "CLOSED"
    assert rows[0]["filled_qty"] == FILLED_QTY
    assert rows[0]["executedQty"] == FILLED_QTY
    assert rows[0]["exchange_order_id"] == KRAKEN_TXID
    assert fills.aureon_owned_qty("kraken", "ETHUSD") == Decimal(FILLED_QTY)
    assert fills.aureon_net_fill_qty("kraken", "ETHUSD") == Decimal(FILLED_QTY)
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(0)


def test_kraken_buy_records_queryorders_vol_exec_and_not_the_ack(isolated):
    ack = _add_order_ack()
    kraken = _Kraken(ack, queries=[_query_closed(), _query_closed()])
    chain = _chain()
    chain.kraken = kraken
    result = chain._execute_trade({"exchange": "kraken", "symbol": "ETHUSD", "price": 100})

    # The attempt log still treats a body with no error key as FILLED.
    assert result["status"] == "FILLED"
    assert kraken.orders[0] == ("ETHUSD", "buy", Decimal("0.1"))
    assert kraken.queried == [KRAKEN_TXID]
    rows = _rows(isolated)
    assert len(rows) == 1
    assert rows[0]["filled_qty"] == FILLED_QTY
    assert rows[0]["exchange_order_id"] == KRAKEN_TXID
    assert rows[0]["status"] == "CLOSED"
    assert Decimal(rows[0]["filled_qty"]) != kraken.orders[0][2]
    assert fills.aureon_owned_qty("kraken", "ETHUSD") == Decimal(FILLED_QTY)

    chain._execute_trade({"exchange": "kraken", "symbol": "ETHUSD", "price": 100})
    assert len(_rows(isolated)) == 1
    assert fills.aureon_owned_qty("kraken", "ETHUSD") == Decimal(FILLED_QTY)


def test_normalized_kraken_receipt_records_vol_exec(isolated):
    """get_order_status keeps provider status closed and copies vol_exec."""
    ack = _add_order_ack()
    normalized = {
        "status": "no_data",
        "provider_status": "closed",
        "vol_exec": FILLED_QTY,
        "executedQty": None,
        "orderId": KRAKEN_TXID,
        "reason": "missing_or_stale_provider_close_timestamp",
    }
    kraken = _Kraken(ack, repeat=normalized)
    chain = _chain()
    chain.kraken = kraken
    chain._execute_trade({"exchange": "kraken", "symbol": "ETHUSD", "price": 100})

    rows = _rows(isolated)
    assert len(rows) == 1
    assert rows[0]["filled_qty"] == FILLED_QTY
    assert rows[0]["exchange_order_id"] == KRAKEN_TXID
    assert fills.aureon_owned_qty("kraken", "ETHUSD") == Decimal(FILLED_QTY)


@pytest.mark.parametrize("status", ["SUBMITTED", "NEW", "submitted", "new"])
def test_kraken_submitted_or_new_writes_nothing(isolated, status):
    ack = _add_order_ack()
    kraken = _Kraken(
        ack,
        repeat={
            "status": status,
            "vol_exec": FILLED_QTY,
            "executedQty": FILLED_QTY,
            "txid": KRAKEN_TXID,
            "orderId": KRAKEN_TXID,
        },
    )
    chain = _chain()
    chain.kraken = kraken
    result = chain._execute_trade({"exchange": "kraken", "symbol": "ETHUSD", "price": 100})

    assert result["status"] == "FILLED"
    assert kraken.queried == [KRAKEN_TXID] * fills._KRAKEN_QUERY_ATTEMPTS
    assert not isolated.exists()
    assert fills.aureon_owned_qty("kraken", "ETHUSD") == Decimal(0)


@pytest.mark.parametrize("vol_exec", ["1e5000", "NaN", "-0.02", "0", "Infinity"])
def test_kraken_bad_vol_exec_writes_nothing(isolated, vol_exec):
    ack = _add_order_ack()
    kraken = _Kraken(ack, repeat=_query_closed(vol_exec=vol_exec))
    chain = _chain()
    chain.kraken = kraken
    chain._execute_trade({"exchange": "kraken", "symbol": "ETHUSD", "price": 100})

    assert kraken.queried == [KRAKEN_TXID]
    assert not isolated.exists()
    assert fills.aureon_owned_qty("kraken", "ETHUSD") == Decimal(0)
    assert fills.aureon_net_fill_qty("kraken", "ETHUSD") == Decimal(0)


def test_open_kraken_order_is_recorded_when_a_later_query_closes(isolated):
    ack = _add_order_ack()
    opens = [{"status": "open", "vol_exec": "0", "txid": KRAKEN_TXID}] * fills._KRAKEN_QUERY_ATTEMPTS
    kraken = _Kraken(ack, queries=[*opens, _query_closed()])
    assert fills.record_kraken_acknowledged_fill(kraken, "ETHUSD", "buy", ack) is None
    assert not isolated.exists()

    fills.record_kraken_acknowledged_fill(kraken, "ETHUSD", "buy", ack)
    rows = _rows(isolated)
    assert len(rows) == 1
    assert rows[0]["filled_qty"] == FILLED_QTY
    assert rows[0]["exchange_order_id"] == KRAKEN_TXID
    assert fills.aureon_owned_qty("kraken", "ETHUSD") == Decimal(FILLED_QTY)


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


def test_owned_qty_clamps_at_zero_and_net_keeps_the_signed_total(isolated):
    """Buy 0.02, then sells of 0.015 and 0.5. Net is -0.495; owned qty is 0."""
    fills.record_confirmed_fill("binance", "ETHUSDT", "BUY", _response(orderId="884221", executedQty="0.02"))
    fills.record_confirmed_fill(
        "binance", "ETHUSDT", "SELL", _response(orderId="884222", side="SELL", executedQty="0.015")
    )
    fills.record_confirmed_fill(
        "binance", "ETHUSDT", "SELL", _response(orderId="884223", side="SELL", executedQty="0.5")
    )
    assert fills.aureon_net_fill_qty("binance", "ETHUSDT") == Decimal("-0.495")
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(0)


def test_arbitrage_sell_larger_than_the_buy_clamps_that_venue(isolated):
    """Kill-chain keys: Kraken pair ETHUSD, Binance symbol ETHUSDT.

    The sell request stays the buy's filled 0.02. The Binance response filled
    0.5, which is more than the Kraken buy. Owned qty on Binance is 0; the
    signed net is -0.5.
    """
    buy = _response(orderId="K-884221", side="BUY", executedQty="0.02", clientOrderId="ck-kraken-884221")
    sell = _response(orderId="B-884221", side="SELL", executedQty="0.5", clientOrderId="ck-binance-884221")
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
    assert binance.orders == [("ETHUSDT", "SELL", Decimal("0.02"))]
    assert [(row["venue"], row["symbol"], row["filled_qty"]) for row in _rows(isolated)] == [
        ("kraken", "ETHUSD", "0.02"),
        ("binance", "ETHUSDT", "0.5"),
    ]
    assert fills.aureon_owned_qty("kraken", "ETHUSD") == Decimal("0.02")
    assert fills.aureon_net_fill_qty("kraken", "ETHUSD") == Decimal("0.02")
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(0)
    assert fills.aureon_net_fill_qty("binance", "ETHUSDT") == Decimal("-0.5")


@pytest.mark.parametrize("qty", ["1e5000", "1e999999999", "NaN", "Infinity", "-0.02"])
def test_non_finite_negative_and_overflowing_qty_writes_nothing(isolated, qty):
    wrote = fills.record_confirmed_fill(
        "binance",
        "ETHUSDT",
        "BUY",
        _response(orderId="884221", executedQty=qty, filled_qty=qty),
    )
    assert wrote is None
    assert not isolated.exists()
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(0)
    assert fills.aureon_net_fill_qty("binance", "ETHUSDT") == Decimal(0)


def test_overflowing_row_is_skipped_and_a_real_fill_still_counts(isolated):
    isolated.parent.mkdir(parents=True, exist_ok=True)
    good = {
        "venue": "binance",
        "symbol": "ETHUSDT",
        "side": "BUY",
        "status": "FILLED",
        "filled_qty": FILLED_QTY,
        "executedQty": FILLED_QTY,
        "exchange_order_id": ORDER_ID,
        "source": "orca_kill_chain",
    }
    huge = dict(good)
    huge["exchange_order_id"] = "884999"
    huge["filled_qty"] = "1e999999999"
    huge["executedQty"] = "1e999999999"
    isolated.write_text(json.dumps(good) + "\n" + json.dumps(huge) + "\n", encoding="utf-8")
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(FILLED_QTY)
    assert fills.aureon_net_fill_qty("binance", "ETHUSDT") == Decimal(FILLED_QTY)


def test_overflow_while_totaling_fails_closed_to_zero(isolated, monkeypatch):
    isolated.parent.mkdir(parents=True, exist_ok=True)
    isolated.write_text(json.dumps({
        "venue": "binance",
        "symbol": "ETHUSDT",
        "side": "BUY",
        "status": "FILLED",
        "filled_qty": FILLED_QTY,
        "executedQty": FILLED_QTY,
        "exchange_order_id": ORDER_ID,
        "source": "orca_kill_chain",
    }) + "\n", encoding="utf-8")

    def _huge(_payload):
        return Decimal("1e999999999")

    monkeypatch.setattr(fills, "_filled_qty", _huge)
    assert fills.aureon_owned_qty("binance", "ETHUSDT") == Decimal(0)
    assert fills.aureon_net_fill_qty("binance", "ETHUSDT") == Decimal(0)


def _ledger_worker(path: str, order_ids: list[str], noop: bool, barrier) -> None:
    """Child writer. A no-op flock waits inside the locked section so both snapshot the same file."""
    if noop:
        fills.fcntl.flock = lambda *_args, **_kwargs: None
        fills._after_read = barrier.wait
    for order_id in order_ids:
        wrote = fills.record_confirmed_fill(
            "binance",
            "ETHUSDT",
            "BUY",
            {"status": "FILLED", "orderId": order_id, "executedQty": FILLED_QTY, "side": "BUY"},
            ledger_path=path,
        )
        if wrote is None:
            raise RuntimeError(order_id)


def _run_writers(path, count: int, noop: bool) -> list[dict]:
    ctx = multiprocessing.get_context("fork")
    barrier = ctx.Barrier(2) if noop else None
    procs = [
        ctx.Process(
            target=_ledger_worker,
            args=(str(path), [f"P{slot}-{i}" for i in range(count)], noop, barrier),
        )
        for slot in (0, 1)
    ]
    for proc in procs:
        proc.start()
    for proc in procs:
        proc.join(60)
        if proc.is_alive():
            proc.kill()
            proc.join()
            raise AssertionError(f"writer pid {proc.pid} hung")
        assert proc.exitcode == 0, proc.exitcode
    return _rows(path)


def test_two_processes_keep_every_fill_only_while_flock_works(tmp_path):
    """2 processes x 400 fills. All 800 land with flock.

    With flock replaced by a no-op, both processes snapshot the file and the
    later replace drops the other process's row, so 400 of 800 remain.
    """
    kept = _run_writers(tmp_path / "kept.jsonl", 400, noop=False)
    assert len(kept) == 800
    assert len({row["exchange_order_id"] for row in kept}) == 800

    dropped = _run_writers(tmp_path / "dropped.jsonl", 400, noop=True)
    assert len(dropped) == 400
    assert len({row["exchange_order_id"] for row in dropped}) == 400
