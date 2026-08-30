from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "aureon" / "trading" / "aureon_the_play.py"


class _Bus:
    def __init__(self) -> None:
        self.thoughts: list[Any] = []

    def publish(self, thought: Any) -> None:
        self.thoughts.append(thought)


class _Hive:
    def __init__(self) -> None:
        self.updates: list[dict[str, Any]] = []

    def update(self, **kwargs: Any) -> None:
        self.updates.append(kwargs)


class _Mycelium:
    def __init__(self) -> None:
        self.broadcasts: list[tuple[str, dict[str, Any]]] = []
        self.propagations: list[tuple[str, dict[str, Any]]] = []

    def broadcast_signal(self, name: str, payload: dict[str, Any]) -> None:
        self.broadcasts.append((name, payload))

    def propagate_to_all(self, name: str, payload: dict[str, Any]) -> int:
        self.propagations.append((name, payload))
        return 1


class _RawBinance:
    dry_run = False

    def __init__(self) -> None:
        self.mutation_calls = 0

    def get_free_balance(self, asset: str) -> float:
        assert asset == "BTC"
        return 1.0

    def place_market_order(self, *args: Any, **kwargs: Any) -> None:
        self.mutation_calls += 1


class _Log:
    def info(self, *args: Any, **kwargs: Any) -> None:
        return None

    def warning(self, *args: Any, **kwargs: Any) -> None:
        return None


def _isolated_trader_class() -> type:
    """Compile only the integration methods, avoiding legacy import side effects."""

    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    original = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "AureonThePlayTrader"
    )
    selected = {
        "_install_unity_exchange_brain",
        "_governed_client_for",
        "_governed_execution_confirmed",
        "recent_economic_sensations",
        "_exit_managed_position",
    }
    isolated = ast.ClassDef(
        name="IsolatedAureonThePlayTrader",
        bases=[],
        keywords=[],
        body=[
            node
            for node in original.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in selected
        ],
        decorator_list=[],
    )
    module = ast.fix_missing_locations(ast.Module(body=[isolated], type_ignores=[]))
    namespace: dict[str, Any] = {"Any": Any, "logger": _Log()}
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return namespace["IsolatedAureonThePlayTrader"]


def test_the_play_hold_is_felt_and_cannot_remove_position() -> None:
    trader_type = _isolated_trader_class()
    trader = object.__new__(trader_type)
    raw = _RawBinance()
    trader.client = raw
    trader.thought_bus = _Bus()
    trader.mycelium = _Mycelium()
    hive = _Hive()
    trader._install_unity_exchange_brain(
        unity_composition=None,
        unity_plan_supplier=None,
        trusted_unity_plan_supplier_ids=(),
        hive_state=hive,
    )
    trader.dry_run = False
    trader.positions = {
        "BTCUSDT": {"size": 10.0, "quote": "USDT", "entry_price": 90.0}
    }
    trader.total_profit = 0.0

    result = trader._exit_managed_position(
        "BTCUSDT", trader.positions["BTCUSDT"], 100.0, 0.1
    )

    assert result["decision"] == "HOLD"
    assert raw.mutation_calls == 0
    assert "BTCUSDT" in trader.positions
    assert trader.total_profit == 0.0
    sensations = trader.recent_economic_sensations()
    assert len(sensations) == 1
    assert sensations[0]["felt_state"] == "PROTECTIVE_HOLD"
    assert sensations[0]["not_human_sensation"] is True
    assert len(trader.thought_bus.thoughts) == 1
    assert len(hive.updates) == 1
    assert len(trader.mycelium.broadcasts) == 1
    assert len(trader.mycelium.propagations) == 1


def test_the_play_source_has_one_governed_buy_sell_door() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    constructor = source[
        source.index("class AureonThePlayTrader:") : source.index(
            "    def load_existing_positions("
        )
    ]

    assert "unity_composition: Any = None" in constructor
    assert "OrganismEconomicSensationRouter" in constructor
    assert "build_queen_exchange_brains" in constructor
    assert "outcome_observer=self._economic_sensation_router.observe" in constructor
    assert "self.client = brains[\"binance\"]" in constructor
    assert source.count('self._governed_client_for("binance").place_market_order(') == 2
    assert "self.client.place_market_order(" not in source
    assert "self.close_position(" not in source
    assert source.count("self._exit_managed_position(") == 6
    assert "def recent_economic_sensations" in source
    assert "if not self._governed_execution_confirmed(res):" in source
    assert "if not self._governed_execution_confirmed(result):" in source
