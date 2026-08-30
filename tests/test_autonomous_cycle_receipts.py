from __future__ import annotations

import time

from aureon.autonomous import aureon_autonomous_cycle as cycle


class Balance(dict):
    def __init__(self, amount: float, now: float):
        super().__init__({"GBP": amount})
        self.truth_status = "real_derived"
        self.generated_values = False
        self.source_timestamp = now - 1.0
        self.received_at = now
        self.source_ids = ["capital_account:primary"]


def terminal_fill(side: str, deal_id: str, now: float) -> dict:
    return {
        "status": "filled",
        "truth_status": "real_observed",
        "generated_values": False,
        "terminal_fill": True,
        "terminal_fill_receipt_complete": True,
        "eligible_for_state": True,
        "eligible_for_pnl": True,
        "eligible_for_learning": True,
        "provider_order_id": f"order-{side.lower()}",
        "provider_deal_id": deal_id,
        "source_id": f"capital_confirmation:order-{side.lower()}",
        "source_timestamp": now - 1.0,
        "received_at": now,
        "filled_qty": 0.01,
        "filled_avg_price": 10.0,
        "fee_amount": 0.01,
        "fee_currency": "GBP",
        "side": side,
    }


class FakeCapital:
    enabled = True
    cst = "session"

    def __init__(self, now: float):
        self.now = now
        self.place_result: dict = {"status": "submitted", "dealReference": "pending-open"}
        self.confirm_result: dict = {"status": "pending", "dealReference": "pending-open"}
        self.close_result: dict = {"status": "submitted", "dealReference": "pending-close"}
        self.place_calls = 0
        self.confirm_calls = 0
        self.close_calls = 0

    def get_account_balance(self):
        return Balance(100.0, self.now)

    def get_ticker(self, symbol: str):
        return {
            "symbol": symbol,
            "price": 10.0,
            "bid": 9.9,
            "ask": 10.1,
            "truth_status": "real_derived",
            "generated_values": False,
            "action_eligible": True,
            "source_id": "capital_market:COPPER",
            "source_timestamp": self.now - 1.0,
            "received_at": self.now,
        }

    def get_positions(self):
        return []

    def get_positions_with_fees(self):
        return []

    def place_market_order(self, *_args):
        self.place_calls += 1
        return self.place_result

    def confirm_order(self, _reference: str):
        self.confirm_calls += 1
        return self.confirm_result

    def close_position(self, _deal_id: str):
        self.close_calls += 1
        return self.close_result


def test_default_cli_is_inert(capsys):
    assert cycle.main([]) == 0
    assert "default invocation is inert" in capsys.readouterr().out


def test_missing_evidence_is_numeric_free_no_data():
    class Incomplete(FakeCapital):
        def get_account_balance(self):
            return {"GBP": 100.0}

        def get_ticker(self, _symbol: str):
            return {"price": 10.0}

    client = Incomplete(time.time())
    agent = cycle.AutonomousAgent(client)
    assert agent.get_energy() is None
    valid, price = agent.scan_reality()
    assert valid is False
    assert price is None
    assert agent.last_no_data["actionable"] is False
    assert agent.last_no_data["eligible_for_accounting"] is False


def test_submission_ack_is_pending_and_does_not_duplicate():
    now = time.time()
    client = FakeCapital(now)
    agent = cycle.AutonomousAgent(client, live_actions_enabled=True)
    valid, price = agent.scan_reality()
    assert valid is True
    assert agent.deploy_capital(price) is False
    assert agent.active_deal_id is None
    assert agent.pending_deal_reference == "pending-open"
    assert client.place_calls == 1

    assert agent.deploy_capital(price) is False
    assert client.place_calls == 1
    assert client.confirm_calls == 1
    assert agent.active_deal_id is None


def test_only_terminal_fee_complete_fills_mutate_lifecycle():
    now = time.time()
    client = FakeCapital(now)
    client.place_result = terminal_fill("BUY", "deal-1", now)
    agent = cycle.AutonomousAgent(client, live_actions_enabled=True)
    valid, price = agent.scan_reality()
    assert valid is True
    assert agent.deploy_capital(price) is True
    assert agent.active_deal_id == "deal-1"

    assert agent.monitor_harvest() == "NO_DATA"
    assert agent.active_deal_id == "deal-1"

    client.close_result = terminal_fill("SELL", "deal-1", now)
    assert agent.execute_kill() is True
    assert agent.active_deal_id is None
    assert client.close_calls == 1
