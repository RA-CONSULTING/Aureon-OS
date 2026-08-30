import importlib.util
import json
import time
from pathlib import Path

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "aureon"
    / "command_centers"
    / "aureon_war_band.py"
)
SPEC = importlib.util.spec_from_file_location("war_band_receipt_lifecycle", MODULE_PATH)
war_band = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(war_band)


def _quote(now: float) -> dict:
    return {
        "status": "live",
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "source_id": "kraken:/0/public/Ticker",
        "source_timestamp": now,
        "received_at": now,
        "receipt_id": "quote-btcusd-1",
        "symbol": "BTC/USD",
        "price": 10.0,
        "bid": 9.99,
        "ask": 10.01,
    }


def _position(now: float) -> dict:
    return {
        "symbol": "BTC/USD",
        "exchange": "kraken",
        "quantity": 2.0,
        "entry_price": 8.0,
        "entry_value": 16.0,
        "entry_fee": 0.1,
        "entry_fee_currency": "USD",
        "quote_currency": "USD",
        "entry_order_id": "entry-order-1",
        "entry_fill_ids": ["entry-fill-1"],
        "entry_fill_receipt_complete": True,
        "entry_accounting_eligible": True,
        "source_id": "kraken_order:entry-order-1",
        "source_timestamp": now - 10.0,
        "received_at": now - 9.0,
        "receipt_id": "entry-receipt-1",
        "truth_status": "real_observed",
        "generated_values": False,
    }


def _terminal_fill(now: float, *, symbol: str = "BTC/USD") -> dict:
    return {
        "status": "FILLED",
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "source_id": "kraken_order:close-order-1",
        "source_timestamp": now,
        "received_at": now,
        "receipt_id": "close-receipt-1",
        "orderId": "close-order-1",
        "symbol": symbol,
        "side": "SELL",
        "filled_qty": 2.0,
        "filled_avg_price": 10.0,
        "filled_notional": 20.0,
        "fee": 0.2,
        "fee_currency": "USD",
        "fills": [{"tradeId": "close-fill-1"}],
        "fill_receipt_complete": True,
        "eligible_for_accounting": True,
        "eligible_for_learning": True,
        "reconciliation_required": False,
    }


class _TrapAdapter:
    def __init__(self, now: float) -> None:
        self.quote = _quote(now)
        self.readback = {
            "status": "pending_reconciliation",
            "data_status": "pending_reconciliation",
            "truth_status": "real_observed",
            "generated_values": False,
        }
        self.quote_calls = 0
        self.submit_calls = 0
        self.readback_calls = 0

    def get_ticker_receipt(self, exchange: str, symbol: str) -> dict:
        assert exchange == "kraken"
        assert symbol == "BTC/USD"
        self.quote_calls += 1
        return dict(self.quote)

    def place_market_order(self, exchange: str, symbol: str, side: str, **kwargs) -> dict:
        assert (exchange, symbol, side) == ("kraken", "BTC/USD", "SELL")
        assert kwargs == {"quantity": 2.0}
        self.submit_calls += 1
        return {
            "status": "pending_reconciliation",
            "data_status": "pending_reconciliation",
            "truth_status": "real_observed",
            "generated_values": False,
            "source_id": "kraken_add_order:close-order-1",
            "orderId": "close-order-1",
            "submitted": True,
            "reconciliation_required": True,
        }

    def get_order_status(self, exchange: str, order_id: str) -> dict:
        assert exchange == "kraken"
        assert order_id == "close-order-1"
        self.readback_calls += 1
        return dict(self.readback)


def _band(tmp_path: Path, client, now: float):
    band = war_band.WarBand(client, market_pulse=None)
    band.state_file = str(tmp_path / "war-band-state.json")
    state = {"positions": {"BTC/USD": _position(now)}, "kills": []}
    assert band.save_state(state) is True
    return band


def test_close_ack_latches_once_and_only_terminal_fill_mutates_accounting(tmp_path):
    now = time.time()
    client = _TrapAdapter(now)
    band = _band(tmp_path, client, now)

    acknowledged = band._run_sniper()
    assert acknowledged["status"] == "pending_reconciliation"
    assert client.submit_calls == 1
    assert client.readback_calls == 0

    after_ack = band.get_state()
    assert "BTC/USD" in after_ack["positions"]
    assert after_ack["positions"]["BTC/USD"]["quantity"] == 2.0
    assert after_ack["positions"]["BTC/USD"]["entry_value"] == 16.0
    assert after_ack["kills"] == []
    pending = after_ack["positions"]["BTC/USD"]["pending_close"]
    assert pending["submission_attempted"] is True
    assert pending["provider_order_id"] == "close-order-1"

    client.readback = _terminal_fill(time.time(), symbol="ETH/USD")
    mismatched = band._run_sniper()
    assert mismatched["status"] == "pending_reconciliation"
    assert client.submit_calls == 1
    assert client.readback_calls == 1
    assert band.get_state()["kills"] == []
    assert "BTC/USD" in band.get_state()["positions"]

    client.readback = _terminal_fill(time.time())
    settled = band._run_sniper()
    assert settled["status"] == "terminal_fill_settled"
    assert client.submit_calls == 1
    assert client.readback_calls == 2
    assert client.quote_calls == 1
    assert settled["realized_net_pnl"] == pytest.approx(3.7)

    final_state = band.get_state()
    assert final_state["positions"] == {}
    assert len(final_state["kills"]) == 1
    assert final_state["kills"][0]["net_pnl"] == pytest.approx(3.7)
    assert final_state["kills"][0]["accounting_status"] == "terminal_fill_settled"
    assert final_state["settled_provider_order_ids"] == ["close-order-1"]
    assert final_state["settled_provider_fill_ids"] == ["close-fill-1"]
    assert final_state["settled_terminal_receipt_ids"] == ["close-receipt-1"]

    band._run_sniper()
    assert client.submit_calls == 1
    assert client.readback_calls == 2


class _NoReadbackAdapter:
    def __init__(self, now: float) -> None:
        self.quote = _quote(now)
        self.submit_calls = 0

    def get_ticker_receipt(self, exchange: str, symbol: str) -> dict:
        return dict(self.quote)

    def place_market_order(self, *_args, **_kwargs):
        self.submit_calls += 1
        raise AssertionError("submission must be capability-gated before this call")


def test_missing_order_readback_is_not_submitted_and_state_is_unchanged(tmp_path):
    now = time.time()
    client = _NoReadbackAdapter(now)
    band = _band(tmp_path, client, now)
    before = band.get_state()

    result = band._run_sniper()

    assert result["status"] == "not_submitted"
    assert result["data_status"] == "no_data"
    assert client.submit_calls == 0
    assert band.get_state() == before


class _EntryTrapAdapter:
    def __init__(self, now: float) -> None:
        self.quote = _quote(now)
        self.readback = {
            **_terminal_fill(now),
            "receipt_id": "entry-receipt-2",
            "orderId": "entry-order-2",
            "source_id": "kraken_order:entry-order-2",
            "side": "BUY",
            "filled_qty": 1.0,
            "filled_avg_price": 10.0,
            "filled_notional": 10.0,
            "fee": 0.05,
            "fills": [{"tradeId": "entry-fill-2"}],
        }
        self.submit_calls = 0
        self.readback_calls = 0

    def get_ticker_receipt(self, exchange: str, symbol: str) -> dict:
        return dict(self.quote)

    def place_market_order(self, exchange: str, symbol: str, side: str, **kwargs) -> dict:
        assert (exchange, symbol, side) == ("kraken", "BTC/USD", "BUY")
        assert kwargs == {"quote_qty": 10.0}
        self.submit_calls += 1
        return {
            "status": "pending_reconciliation",
            "data_status": "pending_reconciliation",
            "truth_status": "real_observed",
            "generated_values": False,
            "source_id": "kraken_add_order:entry-order-2",
            "orderId": "entry-order-2",
            "submitted": True,
            "reconciliation_required": True,
        }

    def get_order_status(self, exchange: str, order_id: str) -> dict:
        assert (exchange, order_id) == ("kraken", "entry-order-2")
        self.readback_calls += 1
        return dict(self.readback)


def test_entry_ack_latches_once_and_terminal_fill_creates_position(tmp_path):
    now = time.time()
    client = _EntryTrapAdapter(now)
    band = war_band.WarBand(client, market_pulse=None)
    band.scout_size_usd = 10.0
    band.state_file = str(tmp_path / "entry-state.json")
    state = {"positions": {}, "kills": []}
    assert band.save_state(state) is True

    pending = band._deploy_scout("kraken", "BTC/USD", "receipt-test", state)
    assert pending["status"] == "pending_reconciliation"
    assert client.submit_calls == 1
    assert client.readback_calls == 0
    assert state["positions"] == {}
    assert state["pending_entries"]["kraken:BTCUSD"]["provider_order_id"] == "entry-order-2"

    settled = band._deploy_scout("kraken", "BTC/USD", "receipt-test", state)
    assert settled["status"] == "terminal_entry_settled"
    assert client.submit_calls == 1
    assert client.readback_calls == 1
    assert "kraken:BTCUSD" not in state["pending_entries"]
    position = state["positions"]["BTC/USD"]
    assert position["quantity"] == 1.0
    assert position["entry_value"] == 10.0
    assert position["entry_fee"] == 0.05
    assert position["entry_order_id"] == "entry-order-2"
    assert position["entry_fill_ids"] == ["entry-fill-2"]
