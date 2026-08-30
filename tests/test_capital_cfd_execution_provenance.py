import json

from aureon.exchanges import capital_cfd_trader as cfd


NOW = 1_800_000_000.0


class BrainRecorder:
    def __init__(self):
        self.calls = []

    def learn_from_outcome(self, symbol, outcome, *, confidence):
        self.calls.append((symbol, outcome, confidence))
        return {"updated": True}


class CapitalExecutionStub:
    def __init__(self, acknowledgement, confirmation):
        self.acknowledgement = acknowledgement
        self.confirmation = confirmation
        self.close_calls = 0
        self.confirm_calls = 0
        self.market_order_calls = 0

    def close_position(self, deal_id):
        self.close_calls += 1
        return dict(self.acknowledgement)

    def confirm_order(self, deal_reference, *, fee_receipt=None):
        self.confirm_calls += 1
        if callable(self.confirmation):
            return self.confirmation(deal_reference, fee_receipt)
        return dict(self.confirmation)

    def place_market_order(self, *args, **kwargs):
        self.market_order_calls += 1
        raise AssertionError("a close acknowledgement must never create a reverse order")


def _fee_receipt(amount, source_suffix, *, source_timestamp=NOW - 0.5):
    return {
        "amount": amount,
        "currency": "GBP",
        "source_id": f"capital_transaction:{source_suffix}",
        "source_timestamp": source_timestamp,
        "received_at": NOW - 0.25,
        "truth_status": "real_observed",
        "generated_values": False,
    }


def _terminal_receipt(
    deal_reference,
    *,
    deal_id="provider-deal-1",
    side="SELL",
    affected_status="CLOSED",
    price=110.0,
    quantity=2.0,
    fee=0.25,
    source_timestamp=NOW - 2.0,
):
    return {
        "status": "filled",
        "reason": "complete_terminal_provider_fill_receipt",
        "truth_status": "real_observed",
        "provider_order_id": deal_reference,
        "provider_deal_id": deal_id,
        "epic": "AAPL",
        "side": side,
        "filled_qty": quantity,
        "filled_avg_price": price,
        "affected_deals": [{"dealId": deal_id, "status": affected_status}],
        "source_id": f"capital_confirmation:{deal_reference}",
        "source_timestamp": source_timestamp,
        "received_at": NOW - 1.0,
        "generated_values": False,
        "terminal_fill": True,
        "terminal_fill_receipt_complete": True,
        "eligible_for_state": True,
        "eligible_for_pnl": True,
        "eligible_for_learning": True,
        "fee_receipt": _fee_receipt(fee, f"fee-{deal_reference}"),
    }


def _submission_ack(deal_reference):
    return {
        "purpose": "close_position",
        "status": "submitted",
        "reason": "terminal_provider_confirmation_required",
        "truth_status": "real_observed",
        "dealReference": deal_reference,
        "provider_order_id": deal_reference,
        "source_id": f"capital_submission:{deal_reference}",
        "source_timestamp": NOW - 3.0,
        "received_at": NOW - 2.0,
        "generated_values": False,
        "submission_acknowledged": True,
        "terminal_fill": False,
        "terminal_fill_receipt_complete": False,
        "eligible_for_state": False,
        "eligible_for_pnl": False,
        "eligible_for_learning": False,
    }


def _incomplete_confirmation(deal_reference):
    return {
        "status": "filled_unsettled",
        "reason": "provider_fee_receipt_required_for_state_pnl_and_learning",
        "truth_status": "incomplete",
        "provider_order_id": deal_reference,
        "provider_deal_id": "provider-deal-1",
        "source_id": f"capital_confirmation:{deal_reference}",
        "source_timestamp": NOW - 2.0,
        "received_at": NOW - 1.0,
        "generated_values": False,
        "terminal_fill": True,
        "terminal_fill_receipt_complete": False,
        "eligible_for_state": False,
        "eligible_for_pnl": False,
        "eligible_for_learning": False,
    }


def _entry_receipt():
    receipt = _terminal_receipt(
        "open-ref-1",
        side="BUY",
        affected_status="OPENED",
        price=100.0,
        fee=0.5,
        source_timestamp=NOW - 100.0,
    )
    receipt["received_at"] = NOW - 99.0
    receipt["fee_receipt"] = _fee_receipt(
        0.5,
        "entry-fee-1",
        source_timestamp=NOW - 100.0,
    )
    receipt["fee_receipt"]["received_at"] = NOW - 99.0
    return receipt


def _position():
    return cfd.CFDPosition(
        symbol="AAPL",
        deal_id="provider-deal-1",
        epic="AAPL",
        direction="BUY",
        size=2.0,
        entry_price=100.0,
        tp_price=120.0,
        sl_price=90.0,
        asset_class="stock",
        opened_at=NOW - 100.0,
        current_price=99_999.0,
        lifecycle_id="capital-life-1",
        entry_fill_receipt=_entry_receipt(),
        entry_fill_receipt_complete=True,
    )


def _offline_trader(monkeypatch, journal_path, client):
    monkeypatch.setattr(cfd, "CAPITAL_EXECUTION_JOURNAL_PATH", journal_path)
    monkeypatch.setattr(cfd.time, "time", lambda: NOW)
    trader = cfd.CapitalCFDTrader.__new__(cfd.CapitalCFDTrader)
    trader.client = client
    trader.positions = []
    trader._unsettled_provider_positions = {}
    trader.stats = {
        "trades_opened": 0.0,
        "trades_closed": 0.0,
        "winning_trades": 0.0,
        "losing_trades": 0.0,
        "total_pnl_gbp": 0.0,
        "best_trade": 0.0,
        "worst_trade": 0.0,
    }
    trader._execution_journal_loaded = False
    trader._execution_journal_blocked = False
    trader._execution_journal_error = ""
    trader._pending_executions = {}
    trader._completed_executions = {}
    trader._latest_order_error = ""
    trader._last_exchange_sync = 0.0
    trader._latest_monitor_line = ""
    trader._recent_closed_trades = []
    trader._latest_candidate_snapshot = []
    trader._fast_profit_capture_by_deal = {}
    trader._signal_brain = BrainRecorder()
    trader._record_order_lifecycle = lambda *args, **kwargs: None
    trader._publish_learning_update = lambda record: None
    trader._commit_confidence_ratchet = lambda quality, deal_id: None
    trader._ensure_execution_journal_state()
    return trader


def test_delete_ack_stays_pending_without_reverse_order_or_economic_mutation(monkeypatch, tmp_path):
    deal_reference = "close-ref-pending"
    client = CapitalExecutionStub(
        _submission_ack(deal_reference),
        _incomplete_confirmation(deal_reference),
    )
    trader = _offline_trader(monkeypatch, tmp_path / "pending.json", client)
    position = _position()
    trader.positions = [position]

    first = trader._close_position(position, "TP_HIT")
    second = trader._close_position(position, "TP_HIT")

    assert first["status"] == "pending_reconciliation"
    assert second["status"] == "pending_reconciliation"
    assert client.close_calls == 1
    assert client.market_order_calls == 0
    assert client.confirm_calls == 2
    assert trader.positions == [position]
    assert trader.stats["trades_closed"] == 0.0
    assert trader.stats["total_pnl_gbp"] == 0.0
    assert trader._signal_brain.calls == []
    assert trader._recent_closed_trades == []


def test_legacy_success_ack_is_incomplete_and_not_confirmed(monkeypatch, tmp_path):
    client = CapitalExecutionStub(
        {"success": True, "dealReference": "legacy-close-ref"},
        _terminal_receipt("legacy-close-ref"),
    )
    trader = _offline_trader(monkeypatch, tmp_path / "legacy.json", client)
    position = _position()
    trader.positions = [position]

    outcome = trader._close_position(position, "TP_HIT")

    assert outcome["status"] == "pending_reconciliation"
    assert outcome["truth_status"] == "incomplete"
    assert client.close_calls == 1
    assert client.confirm_calls == 0
    assert client.market_order_calls == 0
    assert trader.positions == [position]


def test_terminal_close_uses_observed_fills_and_fees_exactly_once(monkeypatch, tmp_path):
    deal_reference = "close-ref-filled"
    client = CapitalExecutionStub(
        _submission_ack(deal_reference),
        _terminal_receipt(deal_reference),
    )
    trader = _offline_trader(monkeypatch, tmp_path / "filled.json", client)
    position = _position()
    trader.positions = [position]

    record = trader._close_position(position, "TP_HIT")
    repeated = trader._close_position(position, "TP_HIT")

    assert record["status"] == "filled"
    assert record["entry_price"] == 100.0
    assert record["exit_price"] == 110.0
    assert record["gross_pnl"] == 20.0
    assert record["entry_fee"] == 0.5
    assert record["exit_fee"] == 0.25
    assert record["net_pnl"] == 19.25
    assert record["exit_price"] != position.current_price
    assert trader.positions == []
    assert trader.stats["trades_closed"] == 1.0
    assert trader.stats["total_pnl_gbp"] == 19.25
    assert len(trader._signal_brain.calls) == 1
    assert repeated["already_reconciled"] is True
    assert client.close_calls == 1
    assert client.market_order_calls == 0
    assert trader.stats["trades_closed"] == 1.0
    assert len(trader._signal_brain.calls) == 1


def test_restart_reconciles_pending_close_without_resubmission(monkeypatch, tmp_path):
    journal = tmp_path / "restart.json"
    deal_reference = "close-ref-restart"
    first_client = CapitalExecutionStub(
        _submission_ack(deal_reference),
        _incomplete_confirmation(deal_reference),
    )
    first_trader = _offline_trader(monkeypatch, journal, first_client)
    position = _position()
    first_trader.positions = [position]
    assert first_trader._close_position(position, "TP_HIT")["status"] == "pending_reconciliation"

    second_client = CapitalExecutionStub(
        _submission_ack("must-not-submit"),
        _terminal_receipt(deal_reference),
    )
    second_trader = _offline_trader(monkeypatch, journal, second_client)
    second_trader.positions = [position]

    record = second_trader._close_position(position, "TP_HIT")

    assert record["status"] == "filled"
    assert second_client.close_calls == 0
    assert second_client.confirm_calls == 1
    assert second_client.market_order_calls == 0
    assert second_trader.positions == []
    assert second_trader.stats["trades_closed"] == 1.0


def test_stale_terminal_receipt_remains_pending(monkeypatch, tmp_path):
    deal_reference = "close-ref-stale"
    stale = _terminal_receipt(
        deal_reference,
        source_timestamp=NOW - cfd.CAPITAL_EXECUTION_RECEIPT_MAX_AGE_SECS - 1.0,
    )
    client = CapitalExecutionStub(_submission_ack(deal_reference), stale)
    trader = _offline_trader(monkeypatch, tmp_path / "stale.json", client)
    position = _position()
    trader.positions = [position]

    outcome = trader._close_position(position, "TP_HIT")

    assert outcome["status"] == "pending_reconciliation"
    assert outcome["truth_status"] == "incomplete"
    assert trader.positions == [position]
    assert trader.stats["trades_closed"] == 0.0
    assert trader._signal_brain.calls == []


def test_terminal_open_reconciliation_uses_provider_fill_not_decision_quote(monkeypatch, tmp_path):
    deal_reference = "open-ref-terminal"
    receipt = _terminal_receipt(
        deal_reference,
        deal_id="provider-open-deal",
        side="BUY",
        affected_status="OPENED",
        price=123.45,
        quantity=2.0,
        fee=0.2,
    )
    client = CapitalExecutionStub(_submission_ack(deal_reference), receipt)
    trader = _offline_trader(monkeypatch, tmp_path / "open.json", client)
    pending = trader._store_pending_execution({
        "purpose": "open_position",
        "truth_status": "real_observed",
        "reason": "terminal_provider_confirmation_required",
        "deal_reference": deal_reference,
        "lifecycle_id": "capital-open-life",
        "candidate_id": "candidate-1",
        "intent_id": "intent-1",
        "route_key": "capital:AAPL:BUY",
        "symbol": "AAPL",
        "epic": "AAPL",
        "expected_fill_side": "BUY",
        "requested_qty": 2.0,
        "asset_class": "stock",
        "tp_pct": 1.0,
        "sl_pct": 0.5,
        "quality": {},
        "decision_quote": 98_765.0,
    })

    outcome = trader._reconcile_pending_record(pending, force=True)
    position = outcome["position"]

    assert outcome["status"] == "filled"
    assert position.entry_price == 123.45
    assert position.current_price == 123.45
    assert position.entry_price != pending["decision_quote"]
    assert position.deal_id == "provider-open-deal"
    assert position.entry_fill_receipt_complete is True
    assert trader.stats["trades_opened"] == 1.0
    assert json.loads((tmp_path / "open.json").read_text(encoding="utf-8"))["pending"] == {}


def test_provider_visible_position_without_terminal_receipt_is_risk_only(monkeypatch, tmp_path):
    class PositionReader(CapitalExecutionStub):
        def get_positions(self):
            return [{
                "position": {
                    "dealId": "provider-visible-1",
                    "direction": "BUY",
                    "size": 2.0,
                    "level": 100.0,
                    "createdDateUTC": NOW - 10.0,
                },
                "market": {
                    "epic": "AAPL",
                    "symbol": "AAPL",
                    "bid": 100.0,
                    "offer": 101.0,
                    "instrumentType": "SHARES",
                },
                "truth_status": "real_observed",
                "source_id": "capital_position:provider-visible-1",
                "source_timestamp": NOW - 10.0,
                "received_at": NOW - 1.0,
                "generated_values": False,
                "terminal_fill_receipt_complete": False,
                "eligible_for_state": False,
                "eligible_for_pnl": False,
                "eligible_for_learning": False,
            }]

    client = PositionReader(_submission_ack("unused"), _incomplete_confirmation("unused"))
    trader = _offline_trader(monkeypatch, tmp_path / "visible.json", client)

    trader._sync_positions_from_exchange(force=True)

    assert trader.positions == []
    risk_only = trader._unsettled_provider_positions["provider-visible-1"]
    assert risk_only["status"] == "pending_reconciliation"
    assert risk_only["eligible_for_state"] is False
    assert risk_only["eligible_for_pnl"] is False
    assert risk_only["eligible_for_learning"] is False
