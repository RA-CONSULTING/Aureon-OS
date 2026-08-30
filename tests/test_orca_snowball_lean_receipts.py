import importlib
import json
from decimal import Decimal

import aureon.bots.orca_snowball_lean as snowball_module


NOW = 2_000_000_000.0


def _header(receipt_id, *, truth="real_observed", venue=None, symbol=None):
    receipt = {
        "receipt_id": receipt_id,
        "source_id": f"provider:{receipt_id}",
        "data_status": "live",
        "truth_status": truth,
        "generated_values": False,
        "source_timestamp": NOW - 0.5,
        "received_at": NOW - 0.4,
    }
    if venue is not None:
        receipt["venue"] = venue
    if symbol is not None:
        receipt["symbol"] = symbol
    return receipt


class _ReceiptAdapter:
    def __init__(self, *, account_currency="USD"):
        self.account_currency = account_currency
        self.submissions = []
        self.readbacks = []
        self.read_count = 0

    def get_quote_receipt(self, symbol):
        return {
            **_header("quote-1", venue="kraken", symbol=symbol),
            "bid": "105",
            "ask": "106",
            "quote_currency": "USD",
        }

    def get_account_receipt(self):
        return {
            **_header("account-1", venue="kraken"),
            "account_scope": "complete",
            "available_balances": {self.account_currency: "1000"},
        }

    def get_position_receipt(self, symbol):
        return {
            **_header("position-1", venue="kraken", symbol=symbol),
            "position_scope": "complete",
            "cost_basis_complete": True,
            "quantity": "2",
            "cost_basis_total": "180",
            "cost_basis_currency": "USD",
        }

    def get_fee_receipt(self, symbol, side):
        return {
            **_header("fee-1", venue="kraken", symbol=symbol),
            "fee_schedule_complete": True,
            "side": side,
            "fee_currency": "USD",
            "taker_rate": "0.001",
        }

    def submit_order_receipt(self, intent):
        self.submissions.append(dict(intent))
        return {
            **_header("ack-1", venue=intent["venue"], symbol=intent["symbol"]),
            "provider_receipt_type": "KrakenAddOrder",
            "provider_order_id": "order-1",
            "client_order_id": intent["client_order_id"],
            "side": intent["side"],
            "status": "ACK",
        }

    def read_order_receipt(self, unresolved):
        self.read_count += 1
        return self.readbacks.pop(0)


def _gate(request):
    provider_ids = set(request["provider_receipt_ids"].values())
    hnc = {
        **_header("hnc-1", truth="real_derived"),
        "input_receipt_ids": sorted(provider_ids),
        "eligible_for_action": True,
        "hnc_coherence": "0.91",
        "lambda_value": "0.73",
        "phi_alignment": str(snowball_module.PHI),
    }
    auris = {
        **_header("auris-1", truth="real_derived"),
        "input_receipt_ids": sorted(provider_ids | {"hnc-1"}),
        "eligible_for_action": True,
        "auris_coherence": "0.89",
        "auris_resonance": "0.82",
    }
    return {
        **_header("gate-1", truth="real_derived"),
        "input_receipt_ids": sorted(provider_ids | {"hnc-1", "auris-1"}),
        "hnc_receipt": hnc,
        "auris_receipt": auris,
        "eligible_for_action": True,
        "venue": request["venue"],
        "symbol": request["symbol"],
        "side": request["side"],
        "authorization_currency": request["quote_currency"],
        "authorized_notional": "200",
        "authorized_quantity": "1",
        "minimum_net_profit": "1",
    }


def _non_fill(unresolved, status):
    return {
        **_header(
            f"read-{status.lower()}",
            venue=unresolved["venue"],
            symbol=unresolved["symbol"],
        ),
        "provider_receipt_type": "KrakenQueryOrders",
        "provider_order_id": "order-1",
        "client_order_id": unresolved["client_order_id"],
        "side": unresolved["side"],
        "status": status,
    }


def _terminal(unresolved, *, complete=True):
    quantity = Decimal(unresolved["quantity"])
    price = Decimal("106")
    receipt = {
        **_header(
            "fill-1", venue=unresolved["venue"], symbol=unresolved["symbol"]
        ),
        "source_timestamp": NOW - 0.1,
        "received_at": NOW - 0.05,
        "provider_receipt_type": "KrakenQueryOrdersAndTrades",
        "provider_order_id": "order-1",
        "client_order_id": unresolved["client_order_id"],
        "side": unresolved["side"],
        "status": "FILLED",
        "fill_receipt_complete": complete,
        "eligible_for_accounting": complete,
        "eligible_for_learning": complete,
        "reconciliation_required": not complete,
        "filled_quantity": str(quantity),
        "filled_average_price": str(price),
        "filled_notional": str(quantity * price),
        "notional_currency": "USD",
        "fee": "0.2",
        "fee_currency": "USD",
        "provider_timestamp": NOW - 0.1,
    }
    return receipt


def _portfolio_with_capital():
    return {
        **_header("portfolio-live"),
        "portfolio_scope": "complete",
        "total_value": "500",
        "currency": "USD",
    }


def _profit_exit_opportunity():
    return {
        **_header("opportunity-live", truth="real_derived"),
        "opportunities": [
            {
                "type": "PROFIT_EXIT",
                "rank": "9.5",
                "venue": "kraken",
                "symbol": "XBTUSD",
            }
        ],
    }


def test_import_and_zero_portfolio_are_inert_and_bounded(monkeypatch, tmp_path):
    marker = "leave-unchanged"
    monkeypatch.setenv("KRAKEN_API_KEY", marker)
    module = importlib.reload(snowball_module)
    assert module.os.environ["KRAKEN_API_KEY"] == marker

    calls = {"portfolio": 0, "opportunity": 0}

    def portfolio():
        calls["portfolio"] += 1
        return {
            **_header("portfolio-zero"),
            "portfolio_scope": "complete",
            "total_value": "0",
            "currency": "USD",
        }

    def opportunity():
        calls["opportunity"] += 1
        raise AssertionError("zero capital must stop before opportunity reads")

    engine = module.OrcaSnowballLean(
        portfolio_receipt_supplier=portfolio,
        opportunity_receipt_supplier=opportunity,
        state_path=tmp_path / "zero-state.json",
        clock=lambda: NOW,
    )
    outcome = engine.run_cycle()
    assert outcome["status"] == "no_data"
    assert outcome["reason"] == "zero_portfolio_has_no_actionable_capital"
    assert outcome["action"] is False
    assert outcome["accounting"] is False
    assert outcome["learning"] is False
    assert calls == {"portfolio": 1, "opportunity": 0}
    assert engine._doublings_needed(Decimal("0")) is None
    assert engine.scan_arbitrage() == []
    assert engine.scan_momentum() == []
    assert engine.scan_kraken_dips() == []
    assert calls == {"portfolio": 1, "opportunity": 0}


def test_currency_mismatch_cannot_reach_submission(tmp_path):
    adapter = _ReceiptAdapter(account_currency="USDT")
    engine = snowball_module.OrcaSnowballLean(
        receipt_adapters={"kraken": adapter},
        hnc_auris_gate_supplier=_gate,
        state_path=tmp_path / "currency-state.json",
        clock=lambda: NOW,
    )
    outcome = engine.execute_profit_exit(
        {"venue": "kraken", "symbol": "XBTUSD"}
    )
    assert outcome["status"] == "no_data"
    assert outcome["reason"] == "exact_quote_currency_balance_required"
    assert outcome["action"] is False
    assert adapter.submissions == []
    assert not (tmp_path / "currency-state.json").exists()


def test_ack_and_incomplete_fill_survive_restart_then_exact_fill_commits_once(
    tmp_path,
):
    state_path = tmp_path / "snowball-state.json"
    adapter = _ReceiptAdapter()
    engine = snowball_module.OrcaSnowballLean(
        receipt_adapters={"kraken": adapter},
        hnc_auris_gate_supplier=_gate,
        portfolio_receipt_supplier=_portfolio_with_capital,
        opportunity_receipt_supplier=_profit_exit_opportunity,
        state_path=state_path,
        clock=lambda: NOW,
    )

    acknowledgement = engine.run_cycle()
    assert acknowledgement["status"] == "pending_reconciliation"
    assert acknowledgement["action"] is False
    assert acknowledgement["accounting"] is False
    assert acknowledgement["learning"] is False
    assert len(adapter.submissions) == 1
    assert adapter.read_count == 0
    state_after_ack = json.loads(state_path.read_text(encoding="utf-8"))
    unresolved = state_after_ack["unresolved"]
    assert unresolved["provider_order_id"] == "order-1"
    assert state_after_ack["fills"] == []
    assert state_after_ack["realized"] == []

    restarted = snowball_module.OrcaSnowballLean(
        receipt_adapters={"kraken": adapter},
        hnc_auris_gate_supplier=_gate,
        state_path=state_path,
        clock=lambda: NOW,
    )
    adapter.readbacks.append(_non_fill(unresolved, "PARTIALLY_FILLED"))
    partial = restarted.execute_profit_exit(
        {"venue": "kraken", "symbol": "XBTUSD"}
    )
    assert partial["status"] == "pending_reconciliation"
    assert partial["action"] is False
    assert len(adapter.submissions) == 1
    assert adapter.read_count == 1
    assert restarted.trades_executed == 0
    assert restarted.total_profit is None

    adapter.readbacks.append(_terminal(unresolved, complete=False))
    incomplete = restarted.reconcile_unresolved()
    assert incomplete["status"] == "pending_reconciliation"
    assert incomplete["action"] is False
    assert adapter.read_count == 2
    assert restarted.trades_executed == 0

    complete_receipt = _terminal(unresolved)
    adapter.readbacks.append(complete_receipt)
    completed = restarted.reconcile_unresolved()
    assert completed["status"] == "FILLED"
    assert completed["action"] is True
    assert completed["accounting"] is True
    assert completed["learning"] is True
    assert adapter.read_count == 3
    assert len(adapter.submissions) == 1
    assert restarted.trades_executed == 1
    assert restarted.total_profit == Decimal("15.8")
    assert completed["realized"] == {
        "fill_receipt_id": "fill-1",
        "currency": "USD",
        "gross_proceeds": "106",
        "fee": "0.2",
        "allocated_cost_basis": "90",
        "net_profit": "15.8",
    }

    final_bytes = state_path.read_bytes()
    final_state = json.loads(final_bytes.decode("utf-8"))
    assert final_state["unresolved"] is None
    assert final_state["committed_receipt_ids"] == ["fill-1"]
    assert len(final_state["fills"]) == 1
    assert len(final_state["realized"]) == 1

    normalized = restarted._terminal_fill(complete_receipt, unresolved)
    duplicate = restarted._commit_fill(final_state, unresolved, normalized)
    assert duplicate["reason"] == "duplicate_terminal_fill_receipt"
    assert state_path.read_bytes() == final_bytes
    assert restarted.trades_executed == 1
    assert restarted.total_profit == Decimal("15.8")
