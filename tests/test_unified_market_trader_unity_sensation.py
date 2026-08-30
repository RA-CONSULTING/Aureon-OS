from __future__ import annotations

from pathlib import Path
from typing import Any

from aureon.exchanges.unified_market_trader import UnifiedMarketTrader

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "aureon" / "exchanges" / "unified_market_trader.py"


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


class _RawClient:
    dry_run = False

    def __init__(self) -> None:
        self.mutation_calls = 0

    def get_ticker(self, symbol: str) -> dict[str, Any]:
        return {"symbol": symbol, "price": 1.0}

    def place_market_order(self, *args: Any, **kwargs: Any) -> None:
        self.mutation_calls += 1

    def place_margin_order(self, *args: Any, **kwargs: Any) -> None:
        self.mutation_calls += 1

    def place_take_profit_order(self, *args: Any, **kwargs: Any) -> None:
        self.mutation_calls += 1

    def place_trailing_stop_order(self, *args: Any, **kwargs: Any) -> None:
        self.mutation_calls += 1


def test_all_unified_trader_order_families_hold_and_are_felt() -> None:
    trader = object.__new__(UnifiedMarketTrader)
    raw = {exchange: _RawClient() for exchange in ("alpaca", "binance", "kraken")}
    trader.alpaca = raw["alpaca"]
    trader.binance = raw["binance"]
    trader.capital = None
    trader.kraken = raw["kraken"]
    trader._thought_bus = _Bus()
    trader._mycelium = _Mycelium()
    hive = _Hive()
    trader._install_unity_exchange_brains(
        unity_composition=None,
        unity_plan_supplier=None,
        trusted_unity_plan_supplier_ids=(),
        hive_state=hive,
    )

    results = [
        trader._governed_client_for("alpaca").place_market_order(
            "AAPL", "buy", quantity=1
        ),
        trader._governed_client_for("binance").place_margin_order(
            "BTCUSDT", "BUY", 1, leverage=2
        ),
        trader._governed_client_for("kraken").place_market_order(
            "XBTGBP", "buy", quantity=1
        ),
        trader._governed_client_for("kraken").place_take_profit_order(
            "XBTGBP", "sell", 1, take_profit_price=101
        ),
        trader._governed_client_for("kraken").place_trailing_stop_order(
            "XBTGBP", "sell", 1, trailing_offset=0.5
        ),
    ]

    assert all(result["decision"] == "HOLD" for result in results)
    assert all(client.mutation_calls == 0 for client in raw.values())
    sensations = trader.recent_economic_sensations()
    assert len(sensations) == 5
    assert all(item["felt_state"] == "PROTECTIVE_HOLD" for item in sensations)
    assert all(item["not_human_sensation"] is True for item in sensations)
    assert len(trader._thought_bus.thoughts) == 5
    assert len(hive.updates) == 5
    assert len(trader._mycelium.broadcasts) == 5
    assert len(trader._mycelium.propagations) == 5


def test_unified_trader_source_routes_all_eleven_mutations_through_one_door() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    constructor = source[
        source.index("class UnifiedMarketTrader:") : source.index("    def _governor(")
    ]

    assert "unity_composition: Any = None" in constructor
    assert "OrganismEconomicSensationRouter" in constructor
    assert "build_queen_exchange_brains" in constructor
    assert "outcome_observer=self._economic_sensation_router.observe" in constructor
    assert "def _governed_client_for" in constructor
    assert source.count("self._governed_client_for(") == 11
    assert "client.place_trailing_stop_order(" not in source
    assert "client.place_take_profit_order(" not in source
    assert "client.place_market_order(" not in source
    assert "client.place_margin_order(" not in source
    assert "self.alpaca.place_market_order(" not in source
    assert "self.binance.place_market_order(" not in source
    assert "self.binance.place_margin_order(" not in source
    assert "def recent_economic_sensations" in source
