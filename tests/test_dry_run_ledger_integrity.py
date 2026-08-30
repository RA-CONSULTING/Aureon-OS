from __future__ import annotations

import ast
import asyncio
import logging
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parents[1]


def _load_method(
    relative_path: str,
    class_name: str,
    method_name: str,
    extra_globals: Optional[Dict[str, Any]] = None,
):
    source_path = ROOT / relative_path
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    class_node = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    method_node = next(
        node
        for node in class_node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name
    )
    module = ast.Module(body=[method_node], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "Optional": Optional,
        "asyncio": asyncio,
        "logger": logging.getLogger("dry-run-integrity-test"),
        "time": time,
    }
    if extra_globals:
        namespace.update(extra_globals)
    exec(compile(module, str(source_path), "exec"), namespace)
    return namespace[method_name]


def _assert_not_submitted(receipt: Dict[str, Any]) -> None:
    assert receipt["status"] == "not_submitted"
    assert receipt["truth_status"] in {"dry_run", "test_fixture"}
    assert receipt["provider_order_id"] is None
    assert receipt["fill"] is None
    assert receipt["actual_pnl"] is None
    assert receipt["eligible_for_learning"] is False
    assert receipt["generated_values"] is False


def test_live_conversion_dry_run_never_opens_or_teaches() -> None:
    execute_conversion = _load_method(
        "aureon/trading/live_conversion_trader.py",
        "LiveConversionTrader",
        "execute_conversion",
    )
    hub_calls = []
    trader = SimpleNamespace(
        dry_run=True,
        dry_run_attempts=[],
        balances={"USD": 1000.0},
        conversions={},
        conversion_counter=4,
        stats={"conversions_opened": 2},
        last_trade_time={},
        hub=SimpleNamespace(
            record_conversion_outcome=lambda *args: hub_calls.append(args)
        ),
    )
    opportunity = {"from_asset": "USD", "to_asset": "BTC"}

    receipt = asyncio.run(execute_conversion(trader, opportunity))

    _assert_not_submitted(receipt)
    assert trader.dry_run_attempts == [receipt]
    assert trader.conversion_counter == 4
    assert trader.conversions == {}
    assert trader.stats["conversions_opened"] == 2
    assert hub_calls == []


def test_live_conversion_dry_run_has_no_fabricated_balances() -> None:
    load_balances = _load_method(
        "aureon/trading/live_conversion_trader.py",
        "LiveConversionTrader",
        "load_balances",
    )
    trader = SimpleNamespace(
        dry_run=True,
        kraken=SimpleNamespace(get_account_balance=lambda: {"USD": 999.0}),
        balances={"USD": 100.0},
    )

    assert load_balances(trader) is False
    assert trader.balances == {}


def test_orca_dry_run_never_manufactures_or_persists_a_win() -> None:
    class DummyKill:
        pass

    execute_hunt = _load_method(
        "aureon/bots/orca_unleashed.py",
        "OrcaUnleashed",
        "execute_hunt",
        {"OrcaHunt": object, "OrcaKill": DummyKill},
    )
    saved = []
    trader = SimpleNamespace(
        can_trade=lambda: (True, "ok"),
        dry_run_attempts=[],
        session_pnl=7.5,
        session_trades=3,
        session_wins=2,
        trades_this_hour=1,
        _save_state=lambda: saved.append(True),
    )
    hunt = SimpleNamespace(
        symbol="BTCUSD",
        exchange="alpaca",
        direction="long",
        confidence=0.9,
        size_usd=20.0,
        entry_price=100.0,
        target_price=102.0,
        stop_price=99.0,
    )

    receipt = execute_hunt(trader, hunt, dry_run=True)

    _assert_not_submitted(receipt)
    assert trader.dry_run_attempts == [receipt]
    assert trader.session_pnl == 7.5
    assert trader.session_trades == 3
    assert trader.session_wins == 2
    assert trader.trades_this_hour == 1
    assert saved == []


def test_orca_hunt_cycle_excludes_dry_run_receipt_from_completed_kills() -> None:
    class DummyKill:
        pass

    hunt_cycle = _load_method(
        "aureon/bots/orca_unleashed.py",
        "OrcaUnleashed",
        "hunt_cycle",
        {"OrcaKill": DummyKill},
    )
    receipt = {
        "status": "not_submitted",
        "truth_status": "dry_run",
        "provider_order_id": None,
        "fill": None,
        "actual_pnl": None,
        "eligible_for_learning": False,
        "generated_values": False,
    }
    best = SimpleNamespace(symbol="BTCUSD", confidence=0.9)
    trader = SimpleNamespace(
        MIN_CONFIDENCE=0.7,
        can_trade=lambda: (True, "ok"),
        scan_all_markets=lambda: [best],
        execute_hunt=lambda hunt, dry_run: receipt,
        completed_kills=[],
    )

    hunt_cycle(trader, dry_run=True)

    assert trader.completed_kills == []


def test_ultimate_dry_run_never_creates_provider_receipt_or_position() -> None:
    enter_position = _load_method(
        "aureon/trading/aureon_ultimate.py",
        "AureonUltimate",
        "enter_position",
    )
    provider_calls = []
    memory_calls = []
    trader = SimpleNamespace(
        client=SimpleNamespace(
            dry_run=True,
            place_market_order=lambda *args, **kwargs: provider_calls.append((args, kwargs)),
        ),
        primary_quote="USDT",
        allowed_quotes={"USDT"},
        match_quote_asset=lambda symbol: "USDT",
        positions={},
        trades=8,
        memory=SimpleNamespace(
            record_hunt=lambda *args: memory_calls.append(args)
        ),
    )

    receipt = enter_position(
        trader,
        {"symbol": "BTCUSDT"},
        quote_balance=100.0,
        commando="lion",
    )

    _assert_not_submitted(receipt)
    assert trader.last_execution_result == receipt
    assert trader.positions == {}
    assert trader.trades == 8
    assert provider_calls == []
    assert memory_calls == []


def test_queen_dry_run_never_counts_anchors_or_saves_execution() -> None:
    execute_validated_trade = _load_method(
        "aureon/trading/aureon_queen_validated_trader.py",
        "QueenValidatedTrader",
        "execute_validated_trade",
        {"ValidatedTrade": object},
    )
    saves = []
    trade = SimpleNamespace(
        symbol="BTCUSD",
        action="BUY",
        validation_score=1.0,
        coherence=0.95,
        queen_approval=True,
        spore_id="spore-1",
        executed=False,
        execution_result=None,
    )
    trader = SimpleNamespace(
        dry_run=True,
        dry_run_attempts=[],
        executed_trades=[],
        daily_metrics={"trades_executed": 0},
        stargate_engine=SimpleNamespace(),
        mycelium_engine=SimpleNamespace(projected_spores={"spore-1": object()}),
        save_trade_record=lambda value: saves.append(value),
    )

    receipt = asyncio.run(execute_validated_trade(trader, trade))

    _assert_not_submitted(receipt)
    assert trade.executed is False
    assert trade.execution_result == receipt
    assert trader.dry_run_attempts == [receipt]
    assert trader.executed_trades == []
    assert trader.daily_metrics["trades_executed"] == 0
    assert saves == []
