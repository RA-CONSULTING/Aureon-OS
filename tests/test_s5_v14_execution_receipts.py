import importlib
import math
import os
import signal
from types import SimpleNamespace

import aureon.strategies.s5_v14_live_execution as s5_module

NOW = 2_000_000_000.0


def _run_without_event_loop(coroutine):
    """Complete a deliberately no-suspend coroutine without opening sockets."""
    try:
        yielded = coroutine.send(None)
    except StopIteration as completed:
        return completed.value
    coroutine.close()
    raise AssertionError(f"receipt coroutine unexpectedly suspended: {yielded!r}")


class _ScoringEngine:
    def __init__(self):
        self.calls = 0

    def score_entry(self, _symbol, _price, _volume):
        self.calls += 1
        return SimpleNamespace(total_score=8)

    @staticmethod
    def should_enter(score):
        return score.total_score >= 8


class _V14:
    def __init__(self):
        self.scoring_engine = _ScoringEngine()


class _Kraken:
    def __init__(self):
        self.submissions = []
        self.reads = 0
        self.readbacks = []

    def place_market_order(self, *, symbol, side, quantity):
        order_id = f"{side}-{len(self.submissions) + 1}"
        self.submissions.append((order_id, symbol, side, quantity))
        return {
            "orderId": order_id,
            "requestedQty": str(quantity),
            "status": "pending_reconciliation",
            "data_status": "pending_reconciliation",
            "truth_status": "real_observed",
            "generated_values": False,
        }

    def get_order_status(self, order_id):
        self.reads += 1
        if self.readbacks:
            return self.readbacks.pop(0)
        return {
            "orderId": order_id,
            "status": "pending_reconciliation",
            "data_status": "pending_reconciliation",
            "truth_status": "real_observed",
            "generated_values": False,
            "reconciliation_required": True,
        }


def _market(receipt_id, price, timestamp):
    return {
        "symbol": "XBTUSD",
        "price": price,
        "bid": price - 0.1,
        "ask": price + 0.1,
        "volume_24h": 250.0,
        "change_pct": 1.0,
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "source_id": "kraken:/0/public/Ticker+/0/public/Time",
        "source_timestamp": timestamp,
        "received_at": timestamp + 0.01,
        "receipt_id": receipt_id,
        "action": False,
        "accounting": False,
        "learning": False,
    }


def _account(receipt_id, balances):
    return {
        "provider": "kraken",
        "account_scope": "complete",
        "balances": balances,
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "source_id": "kraken:/0/private/Balance",
        "source_timestamp": NOW - 0.1,
        "received_at": NOW - 0.09,
        "receipt_id": receipt_id,
    }


def _gate(market_id, account_id):
    return {
        "source_id": "aureon:hnc_auris_gate",
        "receipt_id": f"gate:{market_id}:{account_id}",
        "input_receipt_ids": [market_id, account_id],
        "source_timestamp": NOW - 0.08,
        "received_at": NOW - 0.07,
        "truth_status": "real_derived",
        "generated_values": False,
        "eligible_for_action": True,
        "earth_open": True,
        "earth_coherence": 0.9,
        "earth_phase_lock": 0.8,
        "earth_phi_boost": 1.1,
        "cosmic_open": True,
        "cosmic_phase": "TEST_PHASE",
        "cosmic_coherence": 0.85,
        "cosmic_distortion": 0.1,
        "cosmic_boost": 1.2,
        "cosmic_joy": 0.7,
        "cosmic_reciprocity": 0.75,
        "planetary_torque": 1.3,
        "lunar_phase": 0.4,
    }


def _terminal(order_id, side, quantity, price, fee, trade_id, timestamp):
    return {
        "orderId": order_id,
        "symbol": "XBTUSD",
        "side": side,
        "status": "FILLED",
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "fill_receipt_complete": True,
        "eligible_for_accounting": True,
        "eligible_for_learning": True,
        "reconciliation_required": False,
        "filled_qty": str(quantity),
        "filled_avg_price": str(price),
        "filled_notional": str(quantity * price),
        "fee": str(fee),
        "fee_currency": "USD",
        "fills": [{"tradeId": trade_id, "source": "kraken_queryorders"}],
        "source_id": f"kraken_order:{order_id}",
        "source_timestamp": timestamp,
        "received_at": timestamp + 0.01,
    }


def test_import_and_constructor_are_inert_and_runtime_fails_closed(monkeypatch):
    marker = "leave-unchanged"
    monkeypatch.setenv("KRAKEN_DRY_RUN", marker)
    original_signal = signal.signal

    def forbidden_signal(*_args, **_kwargs):
        raise AssertionError("signal handlers must not be installed")

    monkeypatch.setattr(signal, "signal", forbidden_signal)
    module = importlib.reload(s5_module)
    engine = module.S5V14LiveEngine()
    assert os.environ["KRAKEN_DRY_RUN"] == marker
    monkeypatch.setattr(signal, "signal", original_signal)
    outcome = _run_without_event_loop(engine.run())

    assert outcome["status"] == "no_data"
    assert outcome["reason"] == (
        "market_account_and_hnc_auris_receipt_adapters_required"
    )
    assert outcome["action"] is False
    assert outcome["accounting"] is False
    assert outcome["learning"] is False
    numeric_values = [
        value
        for value in outcome.values()
        if type(value) in {int, float}
    ]
    assert numeric_values == []


def test_acknowledgements_do_not_mutate_and_terminal_fills_account_once():
    module = s5_module
    kraken = _Kraken()
    v14 = _V14()
    state = {
        "market_id": "market-entry",
        "account": _account("account-entry", {"USD": 1000.0, "BTC": 2.0}),
    }

    def account_supplier():
        return state["account"]

    def gate_supplier():
        return _gate(state["market_id"], state["account"]["receipt_id"])

    engine = module.S5V14LiveEngine(
        starting_capital=10_000.0,
        dry_run=False,
        kraken=kraken,
        v14=v14,
        account_receipt_supplier=account_supplier,
        hnc_auris_gate_receipt_supplier=gate_supplier,
        clock=lambda: NOW,
    )
    assert engine.ingest_market_receipt(
        "BTCUSDT", _market("market-entry", 100.0, NOW - 1.0)
    )["status"] == "accepted"

    acknowledgement = _run_without_event_loop(engine._v14_check("BTCUSDT"))
    assert acknowledgement["status"] == "pending_reconciliation"
    assert len(kraken.submissions) == 1
    assert kraken.reads == 0
    assert engine.positions == {}
    assert engine.closed_trades == []
    assert engine.daily_entries == 0
    assert engine.stats["real_trades_placed"] == 0
    assert engine.stats["entries_approved"] == 0

    still_pending = _run_without_event_loop(engine._v14_check("BTCUSDT"))
    assert still_pending["status"] == "pending_reconciliation"
    assert len(kraken.submissions) == 1
    assert kraken.reads == 1
    assert engine.positions == {}
    assert engine.stats["real_trades_placed"] == 0

    entry_id, _pair, _side, entry_qty = kraken.submissions[0]
    kraken.readbacks.append(
        _terminal(
            entry_id,
            "buy",
            entry_qty,
            100.5,
            0.26,
            "trade-entry",
            NOW - 0.2,
        )
    )
    entry_fill = _run_without_event_loop(engine._v14_check("BTCUSDT"))
    assert entry_fill["status"] == "FILLED"
    assert len(kraken.submissions) == 1
    assert kraken.reads == 2
    assert engine.daily_entries == 1
    assert engine.stats["real_trades_placed"] == 1
    assert engine.stats["entries_approved"] == 1
    position = engine.positions["BTCUSDT"]
    assert position.entry_price == 100.5
    assert position.quantity == entry_qty
    assert position.entry_fee == 0.26
    assert position.entry_fee_currency == "USD"

    state["market_id"] = "market-exit"
    state["account"] = _account(
        "account-exit", {"USD": 900.0, "BTC": 2.0}
    )
    assert engine.ingest_market_receipt(
        "BTCUSDT", _market("market-exit", 102.2, NOW - 0.1)
    )["status"] == "accepted"
    exit_ack = _run_without_event_loop(engine._v14_check("BTCUSDT"))
    assert exit_ack["status"] == "pending_reconciliation"
    assert len(kraken.submissions) == 2
    assert "BTCUSDT" in engine.positions
    assert engine.closed_trades == []
    assert engine.stats["real_trades_placed"] == 1
    assert engine.stats["total_profit"] == 0.0

    exit_id, _pair, _side, exit_qty = kraken.submissions[1]
    exit_receipt = _terminal(
        exit_id,
        "sell",
        exit_qty,
        102.2,
        0.27,
        "trade-exit",
        NOW - 0.02,
    )
    exit_key = f"exit:BTCUSDT:{entry_id}"
    saved_pending = engine._pending_orders[exit_key]
    normalized, reason = engine._terminal_fill_receipt(
        exit_receipt, saved_pending
    )
    assert reason == ""
    assert normalized is not None
    kraken.readbacks.append(exit_receipt)
    exit_fill = _run_without_event_loop(engine._v14_check("BTCUSDT"))

    assert exit_fill["status"] == "FILLED"
    assert len(kraken.submissions) == 2
    assert kraken.reads == 3
    assert "BTCUSDT" not in engine.positions
    assert len(engine.closed_trades) == 1
    assert engine.stats["real_trades_placed"] == 2
    assert engine.stats["exits_profit_target"] == 1
    assert math.isclose(engine.stats["total_profit"], 1.17, abs_tol=1e-12)
    assert engine.stats["realized_pnl_by_currency"] == {
        "USD": engine.stats["total_profit"]
    }

    before = (
        len(engine.closed_trades),
        engine.stats["real_trades_placed"],
        engine.stats["total_profit"],
    )
    duplicate = engine._apply_exit_fill(saved_pending, normalized)
    assert duplicate["reason"] == "duplicate_terminal_fill_receipt"
    assert (
        len(engine.closed_trades),
        engine.stats["real_trades_placed"],
        engine.stats["total_profit"],
    ) == before
