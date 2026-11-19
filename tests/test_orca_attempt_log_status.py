"""Attempt-log labels in orca_executions.json.

On main, a Kraken buy response with no error key is logged as FILLED.
These cases use fake clients only: no network, no orders, no .env.
"""
from __future__ import annotations

import json

import pytest

MODULES = (
    "aureon_radar.bots.orca_unified_kill_chain",
    "aureon.bots.orca_unified_kill_chain",
    "unified_margin_trader.orca_unified_kill_chain",
)

TXID = "OQCLML-BW3P3-BUCMWZ"
ADD_ORDER_ACK = {
    "descr": {"order": "buy 0.20000000 XBTUSD @ market"},
    "txid": [TXID],
}
DRY_RUN_NOT_SUBMITTED = {
    "status": "not_submitted",
    "data_status": "not_submitted",
    "truth_status": "not_submitted",
    "submitted": False,
    "dryRun": True,
    "reason": "dry_run_order_not_submitted",
    "symbol": "XBTUSD",
    "side": "buy",
}
CLOSED_FILL = {
    "status": "closed",
    "vol_exec": "0.20000000",
    "vol": "0.20000000",
    "txid": TXID,
    "descr": {
        "order": "buy 0.20000000 XBTUSD @ market",
        "pair": "XBTUSD",
        "type": "buy",
    },
    "cost": "10000.00000",
    "fee": "26.00000",
    "price": "50000.00000",
}


class _Kraken:
    dry_run = False
    last_balance_source = "live"

    def __init__(self, receipt):
        self.receipt = receipt
        self.calls = []

    def get_account_balance(self):
        return {"ZUSD": "100", "USD": "0"}

    def place_market_order(self, pair, side, volume):
        self.calls.append((pair, side, volume))
        return self.receipt


class _Binance:
    def __init__(self, receipt):
        self.receipt = receipt
        self.calls = []

    def get_free_balance(self, asset):
        return 100.0

    def place_market_order(self, symbol, side, volume):
        self.calls.append((symbol, side, volume))
        return self.receipt


def _load(name):
    return pytest.importorskip(name)


def _quiet(monkeypatch, module):
    for name in ("log_sniper", "log_killer", "log_queen", "log_auris", "log_system"):
        if hasattr(module, name):
            monkeypatch.setattr(module, name, lambda *args, **kwargs: None)


def _chain(module, kraken=None, binance=None):
    chain = module.UnifiedKillChain.__new__(module.UnifiedKillChain)
    chain.kraken = kraken
    chain.binance = binance
    chain.wins_executed = []
    chain.real_portfolio = None
    return chain


def _logged_status(directory):
    path = directory / "orca_executions.json"
    row = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
    return row["result"]["status"]


def _kraken_buy(module, monkeypatch, tmp_path, receipt):
    _quiet(monkeypatch, module)
    monkeypatch.chdir(tmp_path)
    client = _Kraken(receipt)
    chain = _chain(module, kraken=client)
    result = chain._execute_trade({
        "exchange": "kraken",
        "symbol": "XBTUSD",
        "price": 50.0,
        "type": "MOMENTUM",
    })
    assert client.calls == [("XBTUSD", "buy", 0.2)]
    assert result["status"] == _logged_status(tmp_path)
    return result["status"]


def _binance_buy(module, monkeypatch, tmp_path, receipt):
    _quiet(monkeypatch, module)
    monkeypatch.chdir(tmp_path)
    client = _Binance(receipt)
    chain = _chain(module, binance=client)
    result = chain._execute_trade({
        "exchange": "binance",
        "symbol": "BTCUSDT",
        "price": 50.0,
        "type": "MOMENTUM",
    })
    assert client.calls == [("BTCUSDT", "BUY", 0.2)]
    assert result["status"] == _logged_status(tmp_path)
    return result["status"]


@pytest.mark.parametrize("module_name", MODULES)
def test_kraken_dry_run_not_submitted_is_not_filled(module_name, monkeypatch, tmp_path):
    status = _kraken_buy(_load(module_name), monkeypatch, tmp_path, DRY_RUN_NOT_SUBMITTED)
    assert status == "NOT_SUBMITTED"
    assert status != "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
def test_kraken_addorder_ack_is_submitted_unconfirmed(module_name, monkeypatch, tmp_path):
    status = _kraken_buy(_load(module_name), monkeypatch, tmp_path, ADD_ORDER_ACK)
    assert status == "SUBMITTED/UNCONFIRMED"
    assert status != "FILLED"
    assert "status" not in ADD_ORDER_ACK
    assert "executedQty" not in ADD_ORDER_ACK


@pytest.mark.parametrize("module_name", MODULES)
def test_kraken_closed_fill_is_filled(module_name, monkeypatch, tmp_path):
    status = _kraken_buy(_load(module_name), monkeypatch, tmp_path, CLOSED_FILL)
    assert status == "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
def test_kraken_error_list_keeps_real_status(module_name, monkeypatch, tmp_path):
    status = _kraken_buy(
        _load(module_name),
        monkeypatch,
        tmp_path,
        {"error": ["EOrder:Insufficient funds"]},
    )
    assert status == "EOrder:Insufficient funds"
    assert status != "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
def test_kraken_error_string_keeps_real_status(module_name, monkeypatch, tmp_path):
    status = _kraken_buy(
        _load(module_name),
        monkeypatch,
        tmp_path,
        {"error": "below_minimum_trade_value", "symbol": "XBTUSD", "value": 10.0, "min": 63.0},
    )
    assert status == "below_minimum_trade_value"
    assert status != "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
def test_kraken_rejected_without_error_key_is_not_filled(module_name, monkeypatch, tmp_path):
    status = _kraken_buy(
        _load(module_name),
        monkeypatch,
        tmp_path,
        {"status": "rejected", "reason": "Post only order"},
    )
    assert status == "REJECTED"
    assert status != "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
def test_kraken_zero_fill_keeps_closed_status(module_name, monkeypatch, tmp_path):
    status = _kraken_buy(
        _load(module_name),
        monkeypatch,
        tmp_path,
        {"status": "closed", "vol_exec": "0.00000000", "txid": TXID},
    )
    assert status == "CLOSED"
    assert status != "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
def test_kraken_closed_without_txid_is_not_filled(module_name, monkeypatch, tmp_path):
    status = _kraken_buy(
        _load(module_name),
        monkeypatch,
        tmp_path,
        {"status": "closed", "vol_exec": "0.20000000"},
    )
    assert status == "CLOSED"
    assert status != "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
def test_binance_filled_with_executed_qty_is_filled(module_name, monkeypatch, tmp_path):
    status = _binance_buy(
        _load(module_name),
        monkeypatch,
        tmp_path,
        {"status": "FILLED", "executedQty": "0.20000000", "orderId": 123456789},
    )
    assert status == "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
def test_binance_filled_with_executed_qty_none_is_not_filled(
    module_name, monkeypatch, tmp_path
):
    status = _binance_buy(
        _load(module_name),
        monkeypatch,
        tmp_path,
        {"status": "FILLED", "executedQty": None, "orderId": 123456789},
    )
    assert status == "ZERO_FILL"
    assert status != "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
@pytest.mark.parametrize(
    "provider_status",
    ["NEW", "PARTIALLY_FILLED"],
)
def test_binance_non_filled_status_is_not_filled(
    module_name, provider_status, monkeypatch, tmp_path
):
    status = _binance_buy(
        _load(module_name),
        monkeypatch,
        tmp_path,
        {"status": provider_status, "executedQty": "0.20000000", "orderId": 123456789},
    )
    assert status == provider_status
    assert status != "FILLED"


def test_kraken_open_and_inf_are_not_confirmed_fills():
    from aureon.exchanges.orca_attempt_fill import confirmed_exchange_fill

    opened = {"status": "open", "vol_exec": "1.50000000", "txid": TXID}
    infinite = {"status": "closed", "vol_exec": "inf", "txid": TXID}
    assert confirmed_exchange_fill(opened, "kraken") is False
    assert confirmed_exchange_fill(infinite, "kraken") is False


@pytest.mark.parametrize("module_name", MODULES)
def test_binance_filled_with_zero_qty_is_not_filled(module_name, monkeypatch, tmp_path):
    status = _binance_buy(
        _load(module_name),
        monkeypatch,
        tmp_path,
        {"status": "FILLED", "executedQty": "0.00000000", "orderId": 123456789},
    )
    assert status == "ZERO_FILL"
    assert status != "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
def test_binance_rejected_keeps_real_status(module_name, monkeypatch, tmp_path):
    status = _binance_buy(
        _load(module_name),
        monkeypatch,
        tmp_path,
        {"status": "REJECTED", "executedQty": "0", "orderId": 1},
    )
    assert status == "REJECTED"
    assert status != "FILLED"


def test_sully_error_text_filled_is_not_filled_by_attempt_error_status():
    """Error text that is only the word FILLED must not come out as FILLED."""
    from aureon.exchanges.orca_attempt_fill import _attempt_error_status

    for error in ("FILLED", ["FILLED"]):
        label = _attempt_error_status({"error": error}, error)
        assert label == "FAILED"
        assert label != "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
def test_spike_filled_status_with_eorder_error_is_not_filled(
    module_name, monkeypatch, tmp_path
):
    module = _load(module_name)
    receipt = {
        "status": "FILLED",
        "error": ["EOrder:Insufficient funds"],
        "executedQty": "1.0",
    }
    kraken = _kraken_buy(module, monkeypatch, tmp_path, receipt)
    assert kraken == "EOrder:Insufficient funds"
    assert kraken != "FILLED"
    binance = _binance_buy(module, monkeypatch, tmp_path, receipt)
    assert binance == "EOrder:Insufficient funds"
    assert binance != "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
@pytest.mark.parametrize("error", ["FILLED", ["FILLED"]])
def test_error_text_filled_is_not_filled(module_name, error, monkeypatch, tmp_path):
    module = _load(module_name)
    kraken = _kraken_buy(module, monkeypatch, tmp_path, {"error": error})
    assert kraken == "FAILED"
    assert kraken != "FILLED"
    binance = _binance_buy(
        module,
        monkeypatch,
        tmp_path,
        {"status": "FILLED", "executedQty": "1.0", "error": error},
    )
    assert binance == "FAILED"
    assert binance != "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
@pytest.mark.parametrize("provider_status", ["open", "canceled"])
def test_kraken_non_closed_with_fill_qty_is_not_filled(
    module_name, provider_status, monkeypatch, tmp_path
):
    status = _kraken_buy(
        _load(module_name),
        monkeypatch,
        tmp_path,
        {"status": provider_status, "vol_exec": "1.50000000", "txid": TXID},
    )
    assert status == provider_status.upper()
    assert status != "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
@pytest.mark.parametrize("vol_exec", ["inf", "nan"])
def test_kraken_non_finite_vol_exec_is_not_filled(
    module_name, vol_exec, monkeypatch, tmp_path
):
    status = _kraken_buy(
        _load(module_name),
        monkeypatch,
        tmp_path,
        {"status": "closed", "vol_exec": vol_exec, "txid": TXID},
    )
    assert status == "CLOSED"
    assert status != "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
@pytest.mark.parametrize("txid", ["dry_run", "mock_1"])
def test_kraken_sentinel_txid_is_not_filled(module_name, txid, monkeypatch, tmp_path):
    status = _kraken_buy(
        _load(module_name),
        monkeypatch,
        tmp_path,
        {"status": "closed", "vol_exec": "0.20000000", "txid": txid},
    )
    assert status == "CLOSED"
    assert status != "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
def test_dry_run_flag_without_not_submitted_is_not_submitted(
    module_name, monkeypatch, tmp_path
):
    status = _kraken_buy(
        _load(module_name),
        monkeypatch,
        tmp_path,
        {
            "dryRun": True,
            "status": "closed",
            "vol_exec": "0.20000000",
            "txid": TXID,
        },
    )
    assert status == "NOT_SUBMITTED"
    assert status != "FILLED"


@pytest.mark.parametrize("module_name", MODULES)
def test_kraken_status_filled_with_positive_qty_is_unconfirmed(
    module_name, monkeypatch, tmp_path
):
    status = _kraken_buy(
        _load(module_name),
        monkeypatch,
        tmp_path,
        {"status": "FILLED", "vol_exec": "0.20000000", "txid": TXID},
    )
    assert status == "UNCONFIRMED"
    assert status != "FILLED"
    assert status != "ZERO_FILL"


@pytest.mark.parametrize("module_name", MODULES)
def test_kraken_submission_receipt_is_not_filled(module_name, monkeypatch, tmp_path):
    from aureon.exchanges.kraken_client import KrakenClient

    client = KrakenClient.__new__(KrakenClient)
    receipt = client._submission_order_receipt(
        {"descr": {"order": "buy 0.20000000 XBTUSD @ market"}, "txid": [TXID]},
        symbol="XBTUSD",
        side="buy",
        order_type="market",
        requested_quantity="0.2",
    )
    assert receipt["status"] == "pending_reconciliation"
    assert "executedQty" in receipt
    status = _kraken_buy(_load(module_name), monkeypatch, tmp_path, receipt)
    assert status == "PENDING_RECONCILIATION"
    assert status != "FILLED"
