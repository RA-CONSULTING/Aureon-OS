"""Offline receipt-contract tests for MicroProfitLabyrinth execution finalization.

The provider payloads below are fixed test fixtures only.  They never enter
runtime state and no exchange client or network endpoint is contacted.
"""

import asyncio
import copy
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from aureon.trading.micro_profit_labyrinth import LiveBarterMatrix, MicroProfitLabyrinth
from scripts.validation.validate_real_data_contract import scan_text_file


def _opportunity(from_asset: str = "USD", to_asset: str = "BTC") -> SimpleNamespace:
    return SimpleNamespace(
        from_asset=from_asset,
        to_asset=to_asset,
        from_amount=100.0 if from_asset == "USD" else 0.01,
        from_value_usd=100.0,
        expected_pnl_usd=2.0,
        expected_pnl_pct=0.02,
        source_exchange="binance",
        trace_id="offline-receipt-contract",
        executed=False,
        actual_pnl_usd=None,
    )


def _engine() -> MicroProfitLabyrinth:
    engine = object.__new__(MicroProfitLabyrinth)
    engine.pending_reconciliations = {}
    engine._audit_records = []
    engine._audit_event = lambda event_type, payload: engine._audit_records.append(
        (event_type, payload)
    )
    engine._log_order_validation = lambda *args, **kwargs: None
    engine._print_order_validation = lambda *args, **kwargs: None
    return engine


def _binance_buy_trade() -> dict:
    return {
        "status": "success",
        "trade": {"pair": "BTCUSDT", "side": "buy"},
        "result": {
            "orderId": 12345,
            "status": "FILLED",
            "transactTime": int(time.time() * 1000),
            "executedQty": "0.01",
            "cummulativeQuoteQty": "100.0",
            "price": "0",
            "fills": [
                {
                    "tradeId": 67890,
                    "price": "10000",
                    "qty": "0.01",
                    "commission": "0.1",
                    "commissionAsset": "USDT",
                }
            ],
        },
    }


def test_complete_binance_receipt_is_provider_verified() -> None:
    engine = _engine()
    validation = engine._validate_order_execution(
        [_binance_buy_trade()], _opportunity(), "binance"
    )

    assert validation["valid"] is True
    assert validation["receipt_complete"] is True
    assert validation["execution_state"] == "provider_verified"
    assert validation["truth_status"] == "provider_observed"
    assert validation["generated_values"] is False
    assert validation["source_debited_amount"] == pytest.approx(100.0)
    assert validation["target_received_amount"] == pytest.approx(0.01)
    assert validation["avg_buy_price"] == pytest.approx(10000.0)
    assert validation["total_fees"] == pytest.approx(0.1)
    assert validation["source_id"] == "binance:12345"
    assert validation["fill_ids"] == ["67890"]


@pytest.mark.parametrize(
    "mutate, expected_error",
    [
        (
            lambda result: (result.pop("orderId"), result.update(clientOrderId="local-only")),
            "Missing provider order ID",
        ),
        (lambda result: result.update(fills=[]), "Missing provider fill receipts"),
        (lambda result: result.pop("transactTime"), "Missing provider timestamp"),
        (lambda result: result.update(executedQty="0"), "Missing finite filled quantity"),
        (
            lambda result: result["fills"][0].update(commissionAsset="BNB"),
            "Missing observed fee amount",
        ),
    ],
)
def test_missing_provider_evidence_requires_reconciliation(mutate, expected_error) -> None:
    engine = _engine()
    trade = copy.deepcopy(_binance_buy_trade())
    mutate(trade["result"])

    validation = engine._validate_order_execution([trade], _opportunity(), "binance")

    assert validation["valid"] is False
    assert validation["receipt_complete"] is False
    assert validation["execution_state"] == "reconciliation_required"
    assert any(expected_error in error for error in validation["validation_errors"])


def test_kraken_local_adapter_timestamp_is_not_provider_evidence() -> None:
    engine = _engine()
    trade = {
        "status": "success",
        "trade": {"pair": "XBTUSD", "side": "buy"},
        "result": {
            "orderId": "O-PROVIDER",
            "status": "closed",
            "transactTime": int(time.time() * 1000),
            "executedQty": "0.01",
            "cummulativeQuoteQty": "100.0",
            "price": "10000",
            "fee": "0.1",
            "fee_currency": "ZUSD",
            "fills": [{"id": "KRAKEN-FILL-1"}],
        },
    }

    validation = engine._validate_order_execution([trade], _opportunity(), "kraken")

    assert validation["valid"] is False
    assert any(
        "Missing provider timestamp" in error
        for error in validation["validation_errors"]
    )


def test_fee_extraction_never_converts_unknown_currency() -> None:
    engine = _engine()
    result = {
        "fills": [
            {
                "tradeId": 1,
                "commission": "0.001",
                "commissionAsset": "BNB",
            }
        ]
    }

    assert engine._extract_fees(result, "binance", {"pair": "BTCUSDT"}, 10000) is None
    assert engine._extract_fees({"fee": "0.1"}, "generic") is None
    assert engine._extract_fees(
        {"fee": "0.0", "fee_currency": "USD"}, "generic"
    ) == pytest.approx(0.0)


def test_verified_entry_fill_has_no_realized_pnl() -> None:
    engine = _engine()
    validation = engine._validate_order_execution(
        [_binance_buy_trade()], _opportunity(), "binance"
    )

    verification = engine._verify_profit_math(validation, _opportunity(), 0.01)

    assert verification["valid"] is True
    assert verification["receipt_valid"] is True
    assert verification["pnl_verified"] is False
    assert verification["verified_pnl"] is None
    assert verification["pnl_status"] == "not_realized"


class _CostBasisTracker:
    def __init__(self, cost_basis: dict):
        self.cost_basis = cost_basis
        self.recorded = []

    def get_cost_basis(self, asset: str, exchange: str) -> dict:
        return self.cost_basis

    def record_order_execution(self, **receipt) -> None:
        self.recorded.append(receipt)


def test_realized_pnl_requires_provider_backed_entry_and_exit() -> None:
    engine = _engine()
    engine.cost_basis_tracker = _CostBasisTracker(
        {
            "fills_verified": True,
            "last_order_id": "ENTRY-ORDER",
            "last_fills": [{"tradeId": "ENTRY-FILL"}],
            "avg_fill_price": 9000.0,
            "total_quantity": 0.02,
            "total_fees": 0.4,
        }
    )
    opportunity = _opportunity("BTC", "USD")
    validation = {
        "valid": True,
        "receipt_complete": True,
        "exchange": "binance",
        "source_id": "binance:EXIT-ORDER",
        "source_debited_amount": 0.01,
        "target_value_usd": 110.0,
        "total_fees": 0.2,
    }

    verification = engine._verify_profit_math(validation, opportunity, 110.0)

    # Allocated entry cost is 0.01 * 9000 + half of the $0.40 entry fee.
    assert verification["valid"] is True
    assert verification["pnl_verified"] is True
    assert verification["cost_basis_usd"] == pytest.approx(90.2)
    assert verification["verified_pnl"] == pytest.approx(19.6)
    assert verification["truth_status"] == "real_derived"


def test_missing_entry_fee_or_fill_ids_keeps_realized_pnl_no_data() -> None:
    engine = _engine()
    engine.cost_basis_tracker = _CostBasisTracker(
        {
            "fills_verified": True,
            "last_order_id": "ENTRY-ORDER",
            "last_fills": [],
            "avg_fill_price": 9000.0,
            "total_quantity": 0.02,
            "total_fees": None,
        }
    )
    validation = {
        "valid": True,
        "receipt_complete": True,
        "exchange": "binance",
        "source_id": "binance:EXIT-ORDER",
        "source_debited_amount": 0.01,
        "target_value_usd": 110.0,
        "total_fees": 0.2,
    }

    verification = engine._verify_profit_math(
        validation, _opportunity("BTC", "USD"), 110.0
    )

    assert verification["valid"] is False
    assert verification["pnl_verified"] is False
    assert verification["verified_pnl"] is None


def test_verified_pnl_ledger_preserves_exact_provider_derived_value() -> None:
    matrix = object.__new__(LiveBarterMatrix)
    matrix.barter_history = {}
    matrix.profit_ledger = []
    matrix.verified_profit_receipts = []
    matrix.total_realized_profit = 0.0
    matrix.conversion_count = 0

    result = matrix.record_verified_realized_profit(
        from_asset="BTC",
        to_asset="USD",
        from_amount=0.01,
        from_usd=100.0,
        to_amount=1100.0,
        to_usd=1100.0,
        profit_usd=1000.0,
        source_id="binance:EXIT-1",
        source_timestamp=time.time(),
    )

    assert result["profit_usd"] == pytest.approx(1000.0)
    assert result["running_total"] == pytest.approx(1000.0)
    assert result["actual_slippage_pct"] is None
    assert matrix.profit_ledger[0][5] == pytest.approx(1000.0)
    assert matrix.profit_ledger[0][6] == "binance:EXIT-1"
    assert matrix.verified_profit_receipts[0]["generated_values"] is False

    with pytest.raises(ValueError, match="does not reconcile"):
        matrix.record_verified_realized_profit(
            from_asset="BTC",
            to_asset="USD",
            from_amount=0.01,
            from_usd=100.0,
            to_amount=1100.0,
            to_usd=1100.0,
            profit_usd=999.0,
            source_id="binance:EXIT-2",
            source_timestamp=time.time(),
        )


def test_rejected_verified_pnl_ledger_prevents_all_conversion_mutation() -> None:
    engine = _engine()
    engine.balances = {"BTC": 0.01, "USD": 0.0}
    engine.conversions = []
    engine.conversions_made = 0
    engine.total_profit_usd = 0.0

    class _RejectingLedger:
        @staticmethod
        def record_verified_realized_profit(**receipt):
            raise ValueError("receipt mismatch")

    engine.barter_matrix = _RejectingLedger()
    opportunity = _opportunity("BTC", "USD")
    validation = {
        "valid": True,
        "receipt_complete": True,
        "exchange": "binance",
        "source_id": "binance:EXIT-ORDER",
        "source_timestamp": time.time(),
        "source_debited_amount": 0.01,
        "target_received_amount": 110.0,
        "target_value_usd": 110.0,
        "total_fees": 0.2,
    }
    verification = {
        "valid": True,
        "receipt_valid": True,
        "pnl_verified": True,
        "verified_pnl": 19.6,
        "cost_basis_usd": 90.2,
    }

    recorded = engine._record_conversion(
        opportunity, 110.0, validation, verification
    )

    assert recorded is False
    assert engine.balances == {"BTC": 0.01, "USD": 0.0}
    assert engine.conversions == []
    assert engine.conversions_made == 0
    assert engine.total_profit_usd == pytest.approx(0.0)
    assert opportunity.execution_state == "reconciliation_required"


def test_incomplete_receipt_cannot_mutate_conversion_state() -> None:
    engine = _engine()
    engine.balances = {"USD": 100.0, "BTC": 0.0}
    engine.conversions = []
    engine.conversions_made = 0
    engine.total_profit_usd = 7.0
    opportunity = _opportunity()

    recorded = engine._record_conversion(
        opportunity,
        0.01,
        {"valid": False, "receipt_complete": False, "exchange": "binance"},
        {},
    )

    assert recorded is False
    assert engine.balances == {"USD": 100.0, "BTC": 0.0}
    assert engine.conversions == []
    assert engine.conversions_made == 0
    assert engine.total_profit_usd == pytest.approx(7.0)
    assert opportunity.execution_state == "reconciliation_required"
    assert engine._has_pending_reconciliation(opportunity, "binance") is True


def test_verified_entry_updates_position_but_not_profit_learning() -> None:
    engine = _engine()
    engine.balances = {"USD": 100.0, "BTC": 0.0}
    engine.conversions = []
    engine.conversions_made = 0
    engine.total_profit_usd = 7.0
    engine.position_registry = {}
    engine.position_entry_times = {}
    engine.snowball_mode = False
    engine.path_memory = SimpleNamespace(
        record=lambda *args, **kwargs: pytest.fail("entry fill must not train path PnL")
    )
    engine.cost_basis_tracker = _CostBasisTracker({})
    opportunity = _opportunity()
    provider_timestamp = time.time()
    validation = {
        "valid": True,
        "receipt_complete": True,
        "exchange": "binance",
        "source_id": "binance:12345",
        "source_timestamp": provider_timestamp,
        "source_debited_amount": 100.0,
        "target_received_amount": 0.01,
        "source_value_usd": 100.0,
        "target_value_usd": None,
        "total_fees": 0.1,
        "order_ids": [{"order_id": "12345"}],
        "legs": [
            {
                "pair": "BTCUSDT",
                "side": "buy",
                "order_id": "12345",
                "fill_ids": ["67890"],
                "provider_fills": [{"tradeId": "67890"}],
                "execution_price": 10000.0,
            }
        ],
    }
    verification = {
        "valid": True,
        "receipt_valid": True,
        "pnl_verified": False,
        "verified_pnl": None,
        "pnl_status": "not_realized",
    }

    recorded = engine._record_conversion(
        opportunity, 0.01, validation, verification
    )

    assert recorded is True
    assert opportunity.executed is True
    assert opportunity.actual_pnl_usd is None
    assert opportunity.pnl_verified is False
    assert engine.balances == {"USD": 0.0, "BTC": pytest.approx(0.01)}
    assert engine.conversions_made == 1
    assert engine.total_profit_usd == pytest.approx(7.0)
    assert engine.position_registry["BTC"]["source_id"] == "binance:12345"
    assert len(engine.cost_basis_tracker.recorded) == 1


class _CostEstimator:
    def __init__(self) -> None:
        self.samples = []

    def add_sample(self, **sample) -> None:
        self.samples.append(sample)


def test_cost_estimator_learns_only_from_execution_and_quote_receipts() -> None:
    engine = _engine()
    engine.cost_estimator = _CostEstimator()
    opportunity = _opportunity()
    execution_timestamp = time.time()
    validation = {
        "receipt_complete": True,
        "source_id": "binance:12345",
        "source_timestamp": execution_timestamp,
        "notional_usd": 100.0,
        "total_fees": 0.1,
        "legs": [
            {
                "pair": "BTCUSDT",
                "side": "buy",
                "execution_price": 10000.0,
            }
        ],
        "quote_evidence": None,
    }

    assert engine._record_observed_cost_sample(opportunity, validation) is False
    assert engine.cost_estimator.samples == []

    validation["quote_evidence"] = {
        "source_id": "binance-book:BTCUSDT:42",
        "source_timestamp": execution_timestamp - 1.0,
        "bid": 9990.0,
        "ask": 9995.0,
    }
    assert engine._record_observed_cost_sample(opportunity, validation) is True
    assert len(engine.cost_estimator.samples) == 1
    sample = engine.cost_estimator.samples[0]
    assert sample["fee_pct"] == pytest.approx(0.1)
    assert sample["spread_pct"] == pytest.approx((5.0 / 9992.5) * 100.0)
    assert sample["slippage_pct"] == pytest.approx((5.0 / 9995.0) * 100.0)
    assert sample["source_id"] == (
        "binance:12345|binance-book:BTCUSDT:42"
    )


def test_dry_run_finalization_is_not_submitted_and_not_quarantined() -> None:
    engine = _engine()
    opportunity = _opportunity()
    trades = [
        {
            "status": "success",
            "trade": {"pair": "BTCUSDT", "side": "buy"},
            "result": {"dryRun": True},
        }
    ]

    assert engine._finalize_provider_execution(opportunity, trades, "binance") is False
    assert opportunity.executed is False
    assert opportunity.actual_pnl_usd is None
    assert opportunity.execution_state == "not_submitted"
    assert engine.pending_reconciliations == {}


def test_pending_reconciliation_blocks_retry_before_any_execution_gate() -> None:
    engine = _engine()
    opportunity = _opportunity()
    engine._mark_reconciliation_required(
        opportunity, "binance", "submitted order lacks provider fill receipt"
    )

    assert asyncio.run(engine.execute_conversion(opportunity)) is False
    assert opportunity.execution_state == "reconciliation_required"


def test_liquidity_aggregation_preflight_never_submits_provider_orders() -> None:
    engine = _engine()

    class _Provider:
        calls = 0

        @classmethod
        def place_market_order(cls, *args, **kwargs):
            cls.calls += 1
            pytest.fail("non-atomic aggregation must not submit provider orders")

    plan = SimpleNamespace(
        is_profitable=True,
        steps=[
            {
                "action": "SELL",
                "asset": "ETH",
                "amount": 0.1,
                "exchange": "binance",
            },
            {
                "action": "BUY",
                "asset": "BTC",
                "amount_usd": 100.0,
                "exchange": "binance",
            },
        ],
    )

    class _LiquidityEngine:
        executed_aggregations = 0
        total_aggregation_profit = 7.5

        @staticmethod
        def create_aggregation_plan(**kwargs):
            return plan

        @staticmethod
        def print_aggregation_plan(candidate):
            return "offline aggregation preflight"

    engine.binance = _Provider()
    engine.liquidity_engine = _LiquidityEngine()
    engine.exchange_balances = {"binance": {"ETH": 0.1}}
    engine.prices = {"ETH": 1000.0, "BTC": 10000.0}
    engine.asset_momentum = {"ETH": -0.01}

    submitted = asyncio.run(
        engine._attempt_liquidity_aggregation(
            target_asset="BTC",
            target_exchange="binance",
            shortfall_usd=50.0,
            expected_profit_pct=0.02,
        )
    )

    assert submitted is False
    assert _Provider.calls == 0
    assert engine.liquidity_engine.executed_aggregations == 0
    assert engine.liquidity_engine.total_aggregation_profit == pytest.approx(7.5)
    assert engine.pending_reconciliations == {}
    event_types = [event_type for event_type, _ in engine._audit_records]
    assert "execution_not_submitted" in event_types
    assert "liquidity_aggregation_not_submitted" in event_types


def test_cross_exchange_aggregation_plan_is_no_data_before_submission() -> None:
    engine = _engine()
    plan = SimpleNamespace(
        is_profitable=True,
        steps=[
            {
                "action": "SELL",
                "asset": "ETH",
                "amount": 0.1,
                "exchange": "kraken",
            },
            {
                "action": "BUY",
                "asset": "BTC",
                "amount_usd": 100.0,
                "exchange": "binance",
            },
        ],
    )
    engine.liquidity_engine = SimpleNamespace(
        create_aggregation_plan=lambda **kwargs: plan,
        print_aggregation_plan=lambda candidate: "cross-exchange preflight",
    )
    engine.exchange_balances = {}
    engine.prices = {}
    engine.asset_momentum = {}

    submitted = asyncio.run(
        engine._attempt_liquidity_aggregation("BTC", "binance", 50.0, 0.02)
    )

    assert submitted is False
    assert engine.pending_reconciliations == {}
    event_type, payload = engine._audit_records[-1]
    assert event_type == "liquidity_aggregation_no_data"
    assert payload["execution_state"] == "not_submitted"
    assert payload["truth_status"] == "no_data"


def test_ambiguous_nonstandard_exchange_result_is_quarantined() -> None:
    engine = _engine()
    opportunity = _opportunity()

    class _Client:
        @staticmethod
        def get_balance() -> dict:
            return {"USD": 100.0}

        @staticmethod
        def convert_crypto(from_asset: str, to_asset: str, amount: float) -> dict:
            return {"error": "ambiguous adapter response"}

    engine.capital_client = _Client()
    engine._record_failure = lambda *args, **kwargs: pytest.fail(
        "ambiguous post-call response must not feed failure learning"
    )

    assert engine._execute_on_exchange("capital", opportunity, 1.0, {}) is False
    assert opportunity.execution_state == "reconciliation_required"
    assert engine._has_pending_reconciliation(opportunity, "capital") is True


def test_round_trip_missing_navigator_or_liquidity_is_no_data() -> None:
    engine = _engine()
    engine.barter_navigator = None

    allowed, reason = engine.ensure_round_trip_available("USD", "BTC", 100.0)
    assert allowed is False
    assert reason.startswith("NO_DATA")

    engine.barter_navigator = SimpleNamespace(
        find_path=lambda *_: SimpleNamespace(
            hops=[SimpleNamespace(pair="BTCUSDT", exchange="binance")]
        )
    )
    engine.ticker_cache = {"BTCUSDT": {"price": 10000.0}}
    allowed, reason = engine.ensure_round_trip_available("USD", "BTC", 100.0)
    assert allowed is False
    assert "incomplete price/volume receipt" in reason


def test_orca_order_without_provider_sizing_is_not_queued() -> None:
    engine = _engine()
    engine.orca_pending_orders = []

    result = engine.execute_orca_order(
        {
            "hunt_id": "HUNT-1",
            "symbol": "BTC/USD",
            "action": "buy",
            "confidence": 0.8,
            "target_pnl": 1.0,
        }
    )

    assert result["status"] == "no_data"
    assert result["queued"] is False
    assert result["generated_values"] is False
    assert engine.orca_pending_orders == []


def test_orca_order_with_provider_sizing_keeps_source_provenance() -> None:
    engine = _engine()
    engine.orca_pending_orders = []
    source_timestamp = time.time()

    result = engine.execute_orca_order(
        {
            "orca_hunt_id": "HUNT-2",
            "symbol": "BTC/USD",
            "side": "buy",
            "confidence": 0.8,
            "target_pnl_usd": 1.0,
            "from_amount": 100.0,
            "from_value_usd": 100.0,
            "source_exchange": "alpaca",
            "source_id": "orca-provider:HUNT-2",
            "source_timestamp": source_timestamp,
        }
    )

    assert result["status"] == "delegated"
    assert result["queued"] is True
    assert len(engine.orca_pending_orders) == 1
    opportunity = engine.orca_pending_orders[0]
    assert opportunity.from_amount == pytest.approx(100.0)
    assert opportunity.from_value_usd == pytest.approx(100.0)
    assert opportunity.expected_pnl_pct == pytest.approx(0.01)
    assert opportunity.source_id == "orca-provider:HUNT-2"
    assert opportunity.source_timestamp == pytest.approx(source_timestamp)
    assert opportunity.generated_values is False


def test_micro_profit_labyrinth_has_no_real_data_validator_findings() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    target = repo_root / "aureon" / "trading" / "micro_profit_labyrinth.py"

    assert scan_text_file(target, repo_root) == []
