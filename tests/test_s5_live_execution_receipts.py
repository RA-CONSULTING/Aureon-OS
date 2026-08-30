from __future__ import annotations

import asyncio
import importlib
import json
import math
import os
import signal
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import aureon.strategies.s5_live_execution as s5_module
from aureon.governance.durable_contingency import bind_durable_contingency_recovery
from aureon.governance.economic_boundary import (
    CONTINGENCY_WARRANT_SCHEMA,
    ContingencyWarrant,
    EconomicGovernanceBoundary,
)

NOW = 2_000_000_000.0
ACCOUNT_HASH = "a" * 64
HNC_RECEIPT = "hnc:live_field:s5-test"
AURIS_RECEIPT = "auris:cosmic_state:s5-test"


def _allowing_boundary() -> EconomicGovernanceBoundary:
    boundary = Mock(spec=EconomicGovernanceBoundary)
    boundary._boundary_id = "economic-boundary:test-s5-receipts"
    boundary._recovery_capability = object()
    boundary._permit_ttl = Decimal("2")
    boundary._validate_recovered_warrant.return_value = None
    boundary._validate_contingency_reduction.return_value = None
    boundary.prepare_mutation.side_effect = lambda intent: SimpleNamespace(
        permit_id=f"permit:{intent.intent_digest}",
        dual_receipt_id="dual:s5-test",
        proposal_digest="b" * 64,
    )
    boundary.approve_contingency_warrant.side_effect = (
        lambda scope: ContingencyWarrant(
            schema=CONTINGENCY_WARRANT_SCHEMA,
            warrant_id=f"warrant:{scope.scope_digest}",
            boundary_id=boundary._boundary_id,
            scope_digest=scope.scope_digest,
            scope_json=json.dumps(scope.payload(), sort_keys=True, separators=(",", ":")),
            dual_receipt_id="dual:s5-test",
            dual_receipt_json="{}",
            proposal_digest="c" * 64,
            issued_at=str(NOW),
            expires_at=str(NOW + 60),
        )
    )
    boundary.consume_and_call.side_effect = (
        lambda _permit, **kwargs: kwargs["transport"]()
    )
    return boundary


def _recovery_adapter(boundary, state_path):
    adapter_id = "adapter:s5-live-receipts:v1"
    return bind_durable_contingency_recovery(
        adapter_id=adapter_id,
        trusted_adapter_ids=frozenset({adapter_id}),
        boundary=boundary,
        store_path=state_path.with_name(state_path.stem + ".contingency.json"),
        clock=lambda: NOW,
        claim_ttl_s=5.0,
    )


class _KrakenFixture:
    def __init__(self) -> None:
        self.submissions: list[tuple[str, str, str, float]] = []
        self.readbacks: list[dict] = []
        self.reads = 0

    @staticmethod
    def get_ticker_receipt(_pair: str) -> dict:
        raise AssertionError("offline tests must inject market receipts")

    @staticmethod
    def prepare_economic_market_order(
        *,
        symbol: str,
        side: str,
        quantity: float,
        client_order_id: str,
    ) -> dict:
        return {
            "pair": symbol,
            "type": side,
            "ordertype": "market",
            "volume": str(quantity),
            "cl_ord_id": client_order_id,
        }

    def place_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        client_order_id: str,
    ) -> dict:
        order_id = f"order-{len(self.submissions) + 1}"
        self.submissions.append((order_id, symbol, side, quantity))
        return {
            "orderId": order_id,
            "requestedQty": str(quantity),
            "status": "pending_reconciliation",
            "data_status": "pending_reconciliation",
            "truth_status": "real_observed",
            "generated_values": False,
            "cl_ord_id": client_order_id,
        }

    def get_order_status(self, order_id: str) -> dict:
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


class _MyceliumFixture:
    def __init__(self) -> None:
        self.sizes: list[tuple[str, str, float]] = []
        self.scores: list[tuple[str, float]] = []
        self.decisions: list[tuple[str, str, float]] = []
        self.records: list[dict] = []
        self.updates: list[tuple[str, float, bool]] = []

    def s5_calculate_optimal_size(
        self, from_asset: str, to_asset: str, strength: float
    ) -> float:
        self.sizes.append((from_asset, to_asset, strength))
        return 20.0

    def s5_adaptive_labyrinth_score(
        self, path: str, estimated_profit: float
    ) -> float:
        self.scores.append((path, estimated_profit))
        return 0.8

    def should_convert(
        self, from_asset: str, to_asset: str, estimated_profit: float
    ) -> bool:
        self.decisions.append(
            (from_asset, to_asset, estimated_profit)
        )
        return True

    def record_conversion_profit(self, receipt: dict) -> None:
        self.records.append(receipt)

    def s5_update_labyrinth_cache(
        self, path: str, realized_profit: float, success: bool
    ) -> None:
        self.updates.append((path, realized_profit, success))


def _market(receipt_id: str, price: float, timestamp: float) -> dict:
    return {
        "symbol": "XBTUSD",
        "price": price,
        "bid": price - 0.1,
        "ask": price + 0.1,
        "volume_24h": 250.0,
        "change_pct": -1.0,
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


def _account(receipt_id: str, timestamp: float) -> dict:
    return {
        "provider": "kraken",
        "account_scope": "complete",
        "balances": {"USD": 1000.0, "BTC": 2.0},
        "taker_fee_rate": 0.0026,
        "taker_fee_pair": "XBTUSD",
        "provider_receipt_type": "Balance+TradeVolume+Time+KeyInfo",
        "input_receipt_ids": [
            f"{receipt_id}:balance",
            f"{receipt_id}:fee",
            f"{receipt_id}:time",
            f"{receipt_id}:permissions",
        ],
        "account_id_hash": ACCOUNT_HASH,
        "api_key_permission_receipt_id": (
            f"kraken_api_key_permissions:{receipt_id}"
        ),
        "api_key_query_funds": True,
        "api_key_modify_trades": True,
        "api_key_funding_mutations_absent": True,
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "source_id": "kraken:/0/private/Balance",
        "source_timestamp": timestamp,
        "received_at": timestamp + 0.01,
        "receipt_id": receipt_id,
    }


def _gate(
    market_id: str,
    account_id: str,
    timestamp: float,
) -> dict:
    return {
        "source_id": "aureon:hnc_auris_gate",
        "receipt_id": f"gate:{market_id}:{account_id}",
        "input_receipt_ids": [
            market_id,
            account_id,
            HNC_RECEIPT,
            AURIS_RECEIPT,
        ],
        "hnc_receipt_id": HNC_RECEIPT,
        "auris_receipt_id": AURIS_RECEIPT,
        "authorization_receipt_id": "authorization:s5-test",
        "cycle_id": "cycle:s5-test",
        "environment": "live",
        "symbol": "XBTUSD",
        "source_timestamp": timestamp,
        "received_at": timestamp + 0.01,
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


def _partial(order_id: str, quantity: float, timestamp: float) -> dict:
    return {
        "orderId": order_id,
        "symbol": "XBTUSD",
        "side": "buy",
        "status": "PARTIALLY_FILLED",
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "fill_receipt_complete": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "reconciliation_required": True,
        "filled_qty": str(quantity / 2.0),
        "source_id": f"kraken_order:{order_id}",
        "source_timestamp": timestamp,
        "received_at": timestamp + 0.01,
    }


def _terminal(
    order_id: str,
    quantity: float,
    timestamp: float,
) -> dict:
    price = 98.75
    return {
        "receipt_id": f"terminal:{order_id}",
        "orderId": order_id,
        "symbol": "XBTUSD",
        "side": "buy",
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
        "fee": "0.05",
        "fee_currency": "USD",
        "realized_pnl": "0.11",
        "realized_pnl_currency": "USD",
        "fills": [
            {
                "tradeId": "trade-1",
                "source": "kraken_queryorders",
            }
        ],
        "source_id": f"kraken_order:{order_id}",
        "source_timestamp": timestamp,
        "received_at": timestamp + 0.01,
    }


def _assert_trade_state_unchanged(engine, network) -> None:
    assert engine.daily_trades == 0
    assert engine.daily_pnl_by_currency == {}
    assert engine.open_positions == {}
    assert engine._settled_fills == []
    assert engine.stats["real_trades_placed"] == 0
    assert engine.stats["conversions_executed"] == 0
    assert network.records == []
    assert network.updates == []


def test_import_constructor_and_default_cli_are_inert(monkeypatch) -> None:
    marker = "leave-unchanged"
    monkeypatch.setenv("KRAKEN_DRY_RUN", marker)
    original_signal = signal.signal

    def forbidden_signal(*_args, **_kwargs):
        raise AssertionError("inert runtime must not install signal handlers")

    monkeypatch.setattr(signal, "signal", forbidden_signal)
    module = importlib.reload(s5_module)
    engine = module.S5LiveExecutionEngine()
    assert os.environ["KRAKEN_DRY_RUN"] == marker
    assert engine.kraken is None
    assert engine.network is None
    assert engine.dry_run is True
    assert engine.execution_enabled is False
    monkeypatch.setattr(signal, "signal", original_signal)

    outcome = asyncio.run(engine.run())
    assert outcome["status"] == "no_data"
    assert outcome["reason"] == (
        "market_account_and_hnc_auris_receipt_adapters_required"
    )
    assert outcome["action"] is False
    assert outcome["accounting"] is False
    assert outcome["learning"] is False
    assert [
        value
        for value in outcome.values()
        if type(value) in {int, float}
    ] == []
    assert asyncio.run(module.main([])) == 2


def test_dry_run_receipts_never_submit_or_mutate() -> None:
    kraken = _KrakenFixture()
    network = _MyceliumFixture()
    engine = s5_module.S5LiveExecutionEngine(
        dry_run=True,
        kraken=kraken,
        network=network,
        clock=lambda: NOW,
    )
    asyncio.run(
        engine.process_market_receipt(
            "BTCUSDT", _market("dry-market-1", 100.0, NOW - 3.0)
        )
    )
    outcome = asyncio.run(
        engine.process_market_receipt(
            "BTCUSDT", _market("dry-market-2", 99.0, NOW - 2.0)
        )
    )
    assert outcome["status"] == "not_submitted"
    assert outcome["reason"] == "dry_run_order_not_submitted"
    assert kraken.submissions == []
    _assert_trade_state_unchanged(engine, network)


def test_partial_and_ack_do_not_mutate_terminal_fill_commits_once(
    tmp_path,
) -> None:
    kraken = _KrakenFixture()
    network = _MyceliumFixture()
    state = {
        "market_id": "market-2",
        "account": _account("account-2", NOW - 1.8),
    }

    def account_supplier() -> dict:
        return state["account"]

    def gate_supplier() -> dict:
        return _gate(
            state["market_id"],
            state["account"]["receipt_id"],
            NOW - 1.7,
        )

    store = tmp_path / "s5-intents.json"
    boundary = _allowing_boundary()
    engine = s5_module.S5LiveExecutionEngine(
        starting_capital=100.0,
        dry_run=False,
        kraken=kraken,
        network=network,
        account_receipt_supplier=account_supplier,
        hnc_auris_gate_receipt_supplier=gate_supplier,
        economic_governance_boundary=boundary,
        contingency_recovery=_recovery_adapter(boundary, store),
        intent_store_path=store,
        clock=lambda: NOW,
    )
    first = asyncio.run(
        engine.process_market_receipt(
            "BTCUSDT", _market("market-1", 100.0, NOW - 3.0)
        )
    )
    assert first["reason"] == "two_monotonic_market_receipts_required"

    acknowledgement = asyncio.run(
        engine.process_market_receipt(
            "BTCUSDT", _market("market-2", 99.0, NOW - 2.0)
        )
    )
    assert acknowledgement["status"] == "pending_reconciliation", acknowledgement.get("reason")
    assert acknowledgement["accounting"] is False
    assert acknowledgement["learning"] is False
    assert len(kraken.submissions) == 1
    _assert_trade_state_unchanged(engine, network)

    order_id, pair, side, quantity = kraken.submissions[0]
    assert (pair, side) == ("XBTUSD", "buy")
    pending_key = next(iter(engine._pending_intents))
    saved_pending = engine._pending_intents[pending_key]
    kraken.readbacks.append(_partial(order_id, quantity, NOW - 1.1))
    partial = asyncio.run(
        engine.process_market_receipt(
            "BTCUSDT", _market("market-3", 98.9, NOW - 1.2)
        )
    )
    assert partial["status"] == "pending_reconciliation"
    assert kraken.reads == 1
    _assert_trade_state_unchanged(engine, network)

    second_read_same_cycle = engine._reconcile_pending(pending_key)
    assert second_read_same_cycle["reason"] == (
        "order_readback_already_consumed_this_cycle"
    )
    assert kraken.reads == 1
    _assert_trade_state_unchanged(engine, network)

    terminal_receipt = _terminal(order_id, quantity, NOW - 0.2)
    normalized, reason = engine._terminal_fill_receipt(
        terminal_receipt, saved_pending
    )
    assert reason == ""
    assert normalized is not None
    kraken.readbacks.append(terminal_receipt)
    fill = asyncio.run(
        engine.process_market_receipt(
            "BTCUSDT", _market("market-4", 98.8, NOW - 0.4)
        )
    )
    assert fill["status"] == "FILLED"
    assert fill["accounting"] is True
    assert fill["learning"] is True
    assert kraken.reads == 2
    assert len(kraken.submissions) == 1
    assert engine.daily_trades == 1
    assert engine.stats["real_trades_placed"] == 1
    assert engine.stats["conversions_executed"] == 1
    assert len(engine._settled_fills) == 1
    assert order_id in engine.open_positions
    assert engine.daily_pnl_by_currency == {"USD": 0.11}
    assert len(network.records) == 1
    assert len(network.updates) == 1
    assert network.records[0]["net_profit"] == 0.11
    assert network.records[0]["fees"] == 0.05
    assert network.updates[0] == ("USD->BTC", 0.11, True)

    before = (
        engine.daily_trades,
        len(engine._settled_fills),
        len(network.records),
        len(network.updates),
    )
    duplicate = engine._apply_terminal_fill(saved_pending, normalized)
    assert duplicate["reason"] == "duplicate_terminal_fill_receipt"
    assert (
        engine.daily_trades,
        len(engine._settled_fills),
        len(network.records),
        len(network.updates),
    ) == before

    reloaded_network = _MyceliumFixture()
    reloaded = s5_module.S5LiveExecutionEngine(
        dry_run=False,
        kraken=kraken,
        network=reloaded_network,
        account_receipt_supplier=account_supplier,
        hnc_auris_gate_receipt_supplier=gate_supplier,
        intent_store_path=store,
        clock=lambda: NOW,
    )
    assert reloaded._state_load_error is None
    assert reloaded.daily_trades == 1
    assert reloaded.stats["real_trades_placed"] == 1
    assert math.isclose(
        reloaded.daily_pnl_by_currency["USD"], 0.11, abs_tol=1e-12
    )
    assert reloaded_network.records == []
    restarted_duplicate = reloaded._apply_terminal_fill(
        saved_pending, normalized
    )
    assert restarted_duplicate["reason"] == (
        "duplicate_terminal_fill_receipt"
    )
    assert reloaded_network.records == []

    corrupted = json.loads(store.read_text(encoding="utf-8"))
    corrupted["settled_fills"][0]["filled_notional"] = 1.0
    store.write_text(json.dumps(corrupted), encoding="utf-8")
    fail_closed = s5_module.S5LiveExecutionEngine(
        dry_run=False,
        kraken=kraken,
        network=_MyceliumFixture(),
        account_receipt_supplier=account_supplier,
        hnc_auris_gate_receipt_supplier=gate_supplier,
        intent_store_path=store,
        clock=lambda: NOW,
    )
    assert fail_closed._state_load_error == "ValueError"
    assert fail_closed._settled_fills == []
    assert fail_closed.open_positions == {}
    assert fail_closed.daily_pnl_by_currency == {}
    assert fail_closed.stats["real_trades_placed"] == 0
    assert fail_closed.check_runtime_ready() is False
