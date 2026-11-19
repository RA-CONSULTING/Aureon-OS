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
