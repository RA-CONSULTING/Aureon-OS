from __future__ import annotations

from pathlib import Path
from typing import Any

from aureon.bots.gaia_aggressive_reclaimerfix import AggressiveReclaimer

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "aureon" / "bots" / "gaia_aggressive_reclaimerfix.py"


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

    def place_market_order(self, *args: Any, **kwargs: Any) -> None:
        self.mutation_calls += 1


def test_all_gaia_exchanges_hold_without_composition_and_are_felt() -> None:
    gaia = object.__new__(AggressiveReclaimer)
    raw = {exchange: _RawClient() for exchange in ("alpaca", "binance", "kraken")}
    gaia.alpaca = raw["alpaca"]
    gaia.binance = raw["binance"]
    gaia.kraken = raw["kraken"]
    gaia.thought_bus = _Bus()
    gaia.mycelium = _Mycelium()
    hive = _Hive()
    gaia._install_unity_exchange_brains(
        unity_composition=None,
        unity_plan_supplier=None,
        trusted_unity_plan_supplier_ids=(),
        hive_state=hive,
    )

    results = {
        exchange: gaia._governed_client_for(exchange).place_market_order(
            "TESTUSD", "buy", quantity=1
        )
        for exchange in raw
    }

    assert all(result["decision"] == "HOLD" for result in results.values())
    assert all(client.mutation_calls == 0 for client in raw.values())
    sensations = gaia.recent_economic_sensations()
    assert len(sensations) == 3
    assert {item["exchange"] for item in sensations} == set(raw)
    assert all(item["felt_state"] == "PROTECTIVE_HOLD" for item in sensations)
    assert all(item["not_human_sensation"] is True for item in sensations)
    assert len(gaia.thought_bus.thoughts) == 3
    assert len(hive.updates) == 3
    assert len(gaia.mycelium.broadcasts) == 3
    assert len(gaia.mycelium.propagations) == 3


def test_gaia_source_routes_all_eleven_mutations_through_one_resolver() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    constructor = source[
        source.index("class AggressiveReclaimer:") : source.index("    def log(")
    ]

    assert "unity_composition: Any = None" in constructor
    assert "OrganismEconomicSensationRouter" in constructor
    assert "build_queen_exchange_brains" in constructor
    assert "outcome_observer=self._economic_sensation_router.observe" in constructor
    assert "def _governed_client_for" in constructor
    assert source.count("self._governed_client_for(") == 11
    assert "self.alpaca.place_order(" not in source
    assert "self.alpaca.place_market_order(" not in source
    assert "self.binance.place_market_order(" not in source
    assert "self.kraken.place_market_order(" not in source
    assert "def recent_economic_sensations" in source
