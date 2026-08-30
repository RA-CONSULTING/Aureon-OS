from __future__ import annotations

import math
import time

from aureon.autonomous import aureon_full_orchestrator as module


SYMBOL = "TESTUSDC"
VENUE = "kraken"
MARKET_RECEIPT_ID = "kraken:ticker:test"


def market_receipt(now: float, *, venue: str = VENUE) -> dict:
    return {
        "symbol": SYMBOL,
        "venue": venue,
        "price": 10.0,
        "bid": 12.0,
        "ask": 10.1,
        "volume_24h": 100000.0,
        "change_pct": 80.0,
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "source_id": f"{venue}:public-ticker",
        "source_timestamp": now - 1.0,
        "received_at": now,
        "receipt_id": MARKET_RECEIPT_ID,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
    }


def score_receipt(
    now: float,
    key: str,
    value: float,
    input_receipt_ids: list[str],
    *,
    venue: str = VENUE,
) -> dict:
    return {
        key: value,
        "symbol": SYMBOL,
        "venue": venue,
        "truth_status": "real_derived",
        "generated_values": False,
        "source_id": f"aureon:test:{key}",
        "source_timestamp": now - 1.0,
        "received_at": now,
        "receipt_id": f"aureon:test:{key}:receipt",
        "input_receipt_ids": list(input_receipt_ids),
    }


def terminal_fill(
    now: float,
    side: str,
    *,
    order_id: str,
    quantity: float,
    price: float,
    fee: float,
    venue: str = VENUE,
) -> dict:
    notional = quantity * price
    return {
        "status": "FILLED",
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "fill_receipt_complete": True,
        "eligible_for_action": True,
        "eligible_for_accounting": True,
        "eligible_for_learning": True,
        "reconciliation_required": False,
        "orderId": order_id,
        "receipt_id": f"{venue}:fill:{order_id}",
        "source_id": f"{venue}:private-fills",
        "symbol": SYMBOL,
        "venue": venue,
        "side": side,
        "filled_qty": str(quantity),
        "filled_avg_price": str(price),
        "filled_notional": str(notional),
        "fee": str(fee),
        "fee_currency": "USDC",
        "fills": [
            {
                "tradeId": f"trade-{order_id}",
                "qty": str(quantity),
                "price": str(price),
                "fee": str(fee),
                "fee_currency": "USDC",
            }
        ],
        "source_timestamp": now - 1.0,
        "received_at": now,
    }


class ScoreSystem:
    def __init__(
        self,
        now: float,
        key: str,
        value: float,
        *,
        venue: str = VENUE,
    ):
        self.now = now
        self.key = key
        self.value = value
        self.venue = venue

    def evaluate_market_opportunity(self, opportunity: dict) -> dict:
        return score_receipt(
            self.now,
            self.key,
            self.value,
            [opportunity["receipt_id"]],
            venue=self.venue,
        )


class Queen:
    def __init__(self, now: float):
        self.now = now

    def ask_queen_will_we_win(self, **kwargs) -> dict:
        return score_receipt(
            self.now,
            "confidence",
            0.9,
            kwargs["context"]["input_receipt_ids"],
        )


class FakeClient:
    def __init__(self, now: float):
        self.now = now
        self.market = market_receipt(now)
        self.balance = {
            "balances": {"USDC": 100.0},
            "venue": VENUE,
            "data_status": "live",
            "truth_status": "real_observed",
            "generated_values": False,
            "eligible_for_action": True,
            "source_id": "kraken:private-balance",
            "source_timestamp": now - 1.0,
            "received_at": now,
            "receipt_id": "kraken:balance:receipt",
        }
        self.submission = {
            "status": "pending_reconciliation",
            "data_status": "pending_reconciliation",
            "truth_status": "real_observed",
            "generated_values": False,
            "orderId": "pending-buy",
            "receipt_id": "kraken:ack:pending-buy",
            "symbol": SYMBOL,
            "venue": VENUE,
            "side": "BUY",
        }
        self.status_receipt = terminal_fill(
            now,
            "BUY",
            order_id="pending-buy",
            quantity=9.0,
            price=10.0,
            fee=0.1,
        )
        self.place_calls = 0
        self.status_calls = 0
        self.balance_calls = 0
        self.ticker_calls = 0

    def get_24h_tickers(self):
        return [{"symbol": SYMBOL}]

    def get_ticker_receipt(self, _symbol: str):
        self.ticker_calls += 1
        return self.market

    def get_account_balance_receipt(self):
        self.balance_calls += 1
        return self.balance

    def place_market_order(self, *_args, **_kwargs):
        self.place_calls += 1
        return self.submission

    def get_order_status(self, _order_id: str):
        self.status_calls += 1
        return self.status_receipt


def validated_opportunity(
    now: float,
    client: FakeClient,
    *,
    stargate_venue: str = VENUE,
) -> tuple[module.AureonFullOrchestrator, module.Opportunity]:
    state = module.SystemState(
        stargate_active=True,
        quantum_mirror_active=True,
        timeline_validator_active=True,
    )
    orchestrator = module.AureonFullOrchestrator(
        client=client,
        venue=VENUE,
        stargate=ScoreSystem(
            now,
            "resonance",
            0.8,
            venue=stargate_venue,
        ),
        quantum_mirror=ScoreSystem(now, "coherence", 0.8),
        timeline_validator=ScoreSystem(now, "anchor_strength", 0.8),
        queen=Queen(now),
        state=state,
        live_actions_enabled=True,
    )
    opportunities = orchestrator.scan_opportunities()
    assert len(opportunities) == 1
    validated = orchestrator.validate_opportunities(opportunities)
    assert len(validated) == (1 if stargate_venue == VENUE else 0)
    return orchestrator, opportunities[0]


def test_default_cli_and_construction_are_inert(capsys):
    client = object()
    orchestrator = module.AureonFullOrchestrator(client=client)
    assert orchestrator.client is client
    assert orchestrator.venue is None
    assert module.main([]) == 0
    assert "default invocation is inert" in capsys.readouterr().out


def test_hnc_batten_action_gate_requires_same_venue_linked_receipts():
    now = time.time()
    client = FakeClient(now)
    orchestrator, opportunity = validated_opportunity(now, client)

    p1 = min(opportunity.momentum / (100 / module.PHI), 1.0)
    signals = [0.8, 0.8, 0.8]
    mean_signal = sum(signals) / len(signals)
    variance = sum((value - mean_signal) ** 2 for value in signals) / len(signals)
    p2 = 1.0 - min(variance * 2, 1.0)
    p3 = min(math.log10(opportunity.volume + 1) / 5, 1.0)
    expected_batten = (p1 * p2 * p3) ** (1 / 3)
    assert math.isclose(
        opportunity.batten_score,
        expected_batten,
        rel_tol=1e-12,
    )
    assert opportunity.actionable is True
    assert opportunity.accounting_eligible is False
    assert opportunity.learning_eligible is False
    assert opportunity.validation_receipt["eligible_for_action"] is True
    assert len(opportunity.validation_receipt["input_receipt_ids"]) == 6
    assert orchestrator._actionable_validation_receipt(opportunity) is not None
    orchestrator.stargate.venue = "binance"
    assert orchestrator.validate_opportunities([opportunity]) == []
    assert opportunity.actionable is False
    assert opportunity.validation_receipt is None

    wrong_client = FakeClient(now)
    _, wrong_opportunity = validated_opportunity(
        now,
        wrong_client,
        stargate_venue="binance",
    )
    assert wrong_opportunity.actionable is False


def test_missing_balance_provenance_never_submits():
    now = time.time()
    client = FakeClient(now)
    orchestrator, opportunity = validated_opportunity(now, client)
    client.balance.pop("venue")

    assert orchestrator.execute_trade(opportunity, live=True) is False
    assert client.place_calls == 0
    assert orchestrator.state.active_position is None
    assert orchestrator.state.trades_executed == 0


def test_ack_latches_and_one_terminal_readback_is_only_entry_mutation():
    now = time.time()
    client = FakeClient(now)
    orchestrator, opportunity = validated_opportunity(now, client)

    assert orchestrator.execute_trade(opportunity, live=True) is False
    assert client.place_calls == 1
    assert client.balance_calls == 1
    assert client.status_calls == 0
    assert orchestrator.state.active_position is None
    assert orchestrator.state.trades_executed == 0

    assert orchestrator.execute_trade(opportunity, live=True) is True
    assert client.place_calls == 1
    assert client.balance_calls == 1
    assert client.status_calls == 1
    assert orchestrator.pending_order is None
    assert orchestrator.state.trades_executed == 1
    assert orchestrator.state.active_position["entry_order_id"] == "pending-buy"
    assert orchestrator.state.active_position["entry_cost"] == 90.0
    assert orchestrator.state.active_position["entry_fee"] == 0.1

    assert orchestrator.execute_trade(opportunity, live=True) is False
    assert client.place_calls == 1
    assert client.status_calls == 1


def test_ack_without_order_id_latches_and_never_resubmits():
    now = time.time()
    client = FakeClient(now)
    client.submission.pop("orderId")
    orchestrator, opportunity = validated_opportunity(now, client)

    assert orchestrator.execute_trade(opportunity, live=True) is False
    assert orchestrator.pending_order is not None
    assert orchestrator.pending_order["order_id"] == ""
    assert orchestrator.execute_trade(opportunity, live=True) is False
    assert client.place_calls == 1
    assert client.status_calls == 0
    assert orchestrator.state.active_position is None


def test_exit_ack_and_readback_are_realized_only_accounting():
    now = time.time()
    client = FakeClient(now)
    orchestrator, opportunity = validated_opportunity(now, client)
    assert orchestrator.execute_trade(opportunity, live=True) is False
    assert orchestrator.execute_trade(opportunity, live=True) is True

    client.submission = {
        "status": "pending_reconciliation",
        "data_status": "pending_reconciliation",
        "truth_status": "real_observed",
        "generated_values": False,
        "orderId": "pending-sell",
        "receipt_id": "kraken:ack:pending-sell",
        "symbol": SYMBOL,
        "venue": VENUE,
        "side": "SELL",
    }
    client.status_receipt = terminal_fill(
        now,
        "SELL",
        order_id="pending-sell",
        quantity=9.0,
        price=12.0,
        fee=0.2,
    )

    assert orchestrator.check_active_position(target_profit=0.0, live=True) is None
    assert orchestrator.state.active_position is not None
    assert orchestrator.state.total_profit == 0.0
    assert orchestrator.state.trades_won == 0
    ticker_calls_after_submission = client.ticker_calls
    client.market = {"data_status": "no_data"}

    profit = orchestrator.check_active_position(target_profit=0.0, live=True)
    assert math.isclose(profit, 17.7, rel_tol=1e-12)
    assert client.place_calls == 2
    assert client.status_calls == 2
    assert client.ticker_calls == ticker_calls_after_submission
    assert orchestrator.state.active_position is None
    assert math.isclose(orchestrator.state.total_profit, 17.7, rel_tol=1e-12)
    assert orchestrator.state.trades_won == 1


def test_mismatched_terminal_venue_remains_latched_without_accounting():
    now = time.time()
    client = FakeClient(now)
    client.status_receipt = terminal_fill(
        now,
        "BUY",
        order_id="pending-buy",
        quantity=9.0,
        price=10.0,
        fee=0.1,
        venue="binance",
    )
    orchestrator, opportunity = validated_opportunity(now, client)

    assert orchestrator.execute_trade(opportunity, live=True) is False
    assert orchestrator.execute_trade(opportunity, live=True) is False
    assert client.place_calls == 1
    assert client.status_calls == 1
    assert orchestrator.pending_order is not None
    assert orchestrator.state.active_position is None
    assert orchestrator.state.trades_executed == 0
