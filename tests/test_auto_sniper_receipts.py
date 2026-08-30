import importlib.util
import time
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "aureon" / "scanners" / "auto_sniper.py"
SPEC = importlib.util.spec_from_file_location("auto_sniper_receipts", MODULE)
auto_sniper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(auto_sniper)


def _position(now):
    return {
        "exchange": "kraken", "position_status": "OPEN", "provider_position_id": "position-1",
        "quantity": 1.0, "entry_value": 100.0, "entry_fee": 1.0, "fee_currency": "USD",
        "data_status": "live", "truth_status": "real_observed", "generated_values": False,
        "source_id": "kraken:open_positions", "source_timestamp": now, "received_at": now,
        "receipt_id": "position-receipt-1",
    }


def _quote(now, *, generated=False):
    return {
        "price": 110.0, "bid": 109.0, "ask": 111.0,
        "data_status": "live", "truth_status": "real_observed", "generated_values": generated,
        "source_id": "kraken:ticker", "source_timestamp": now, "received_at": now,
        "receipt_id": "quote-receipt-1", "action": False, "accounting": False, "learning": False,
    }


def _fill(now, *, status="FILLED"):
    return {
        "status": status, "fill_receipt_complete": True, "eligible_for_accounting": True,
        "reconciliation_required": False, "provider_order_id": "order-1", "provider_trade_ids": ["trade-1"],
        "executed_quantity": 1.0, "average_price": 110.0, "total_fee": 1.0, "fee_currency": "USD",
        "data_status": "live", "truth_status": "real_observed", "generated_values": False,
        "source_id": "kraken:trades_history", "source_timestamp": now, "received_at": now,
        "receipt_id": "fill-receipt-1",
    }


class FakeClient:
    def __init__(self, quote, fill):
        self.quote = quote
        self.fill = fill
        self.orders = 0

    def get_ticker(self, _exchange, _symbol):
        return self.quote

    def place_market_order(self, *_args, **_kwargs):
        self.orders += 1
        return self.fill


def test_auto_sniper_requires_receipts_and_accounts_one_terminal_fill_atomically(tmp_path):
    assert auto_sniper.main([]) == 0
    now = time.time()
    state = {"positions": {"BTCUSD": _position(now)}, "wins": 0, "total_trades": 0, "harvested": 0.0, "balance": 0.0}
    client = FakeClient(_quote(now, generated=True), _fill(now))
    blocked = auto_sniper.check_and_kill(client, state, state_file=tmp_path / "state.json", now=now)
    assert blocked["data_status"] == "no_data" and blocked["action"] is False
    assert "BTCUSD" in state["positions"] and client.orders == 0

    client.quote = _quote(now)
    client.fill = _fill(now, status="PENDING")
    pending = auto_sniper.check_and_kill(client, state, state_file=tmp_path / "state.json", now=now)
    assert pending["data_status"] == "no_data" and pending["accounting"] is False
    assert "BTCUSD" in state["positions"] and state["harvested"] == 0.0

    client.fill = _fill(now)
    accepted = auto_sniper.check_and_kill(client, state, state_file=tmp_path / "state.json", now=now)
    assert accepted["status"] == "terminal_fills_accounted"
    assert accepted["kills"] == 1 and "BTCUSD" not in state["positions"]
    assert state["settled_terminal_receipt_ids"] == ["fill-receipt-1"]
    assert (tmp_path / "state.json").exists()

    duplicate_state = {"positions": {"BTCUSD": _position(now)}, "settled_terminal_receipt_ids": ["fill-receipt-1"], "settled_provider_trade_ids": ["trade-1"]}
    duplicate = auto_sniper.check_and_kill(client, duplicate_state, state_file=tmp_path / "duplicate.json", now=now)
    assert duplicate["data_status"] == "no_data" and "BTCUSD" in duplicate_state["positions"]
