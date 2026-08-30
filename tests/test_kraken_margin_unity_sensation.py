from __future__ import annotations

from pathlib import Path
from typing import Any

from aureon.core.economic_sensation import OrganismEconomicSensationRouter
from aureon.exchanges.kraken_margin_penny_trader import KrakenMarginArmyTrader

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "aureon" / "exchanges" / "kraken_margin_penny_trader.py"


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


class _RawKraken:
    dry_run = False

    def __init__(self) -> None:
        self.mutation_calls = 0

    def get_ticker(self, symbol: str) -> dict[str, Any]:
        return {"symbol": symbol, "price": 1.0}

    def place_margin_order(self, *args: Any, **kwargs: Any) -> None:
        self.mutation_calls += 1

    def close_margin_position(self, *args: Any, **kwargs: Any) -> None:
        self.mutation_calls += 1


def _wired_trader() -> tuple[
    KrakenMarginArmyTrader,
    _RawKraken,
    _Bus,
    _Hive,
    _Mycelium,
]:
    trader = object.__new__(KrakenMarginArmyTrader)
    raw = _RawKraken()
    bus = _Bus()
    hive = _Hive()
    mycelium = _Mycelium()
    trader.thought_bus = bus
    trader.hive_state = hive
    trader._install_unity_exchange_brain(
        raw_client=raw,
        unity_composition=None,
        unity_plan_supplier=None,
        trusted_unity_plan_supplier_ids=(),
        mycelium_network=mycelium,
    )
    return trader, raw, bus, hive, mycelium


def test_missing_composition_blocks_margin_entry_and_is_felt_once() -> None:
    trader, raw, bus, hive, mycelium = _wired_trader()

    result = trader.client.place_margin_order(
        symbol="XBTGBP",
        side="buy",
        quantity=1,
        leverage=2,
    )

    assert result["decision"] == "HOLD"
    assert result["reason"] == "canonical_queen_unity_composition_required"
    assert raw.mutation_calls == 0
    assert trader.client.get_ticker("XBTGBP")["price"] == 1.0
    sensations = trader.recent_economic_sensations()
    assert len(sensations) == 1
    assert sensations[0]["operation"] == "place_margin_order"
    assert sensations[0]["felt_state"] == "PROTECTIVE_HOLD"
    assert sensations[0]["not_human_sensation"] is True
    assert sensations[0]["delivery"] == {
        "thought_bus": True,
        "hive": True,
        "mycelium": True,
    }
    assert bus.thoughts[0].source == "organism_economic_sensation"
    assert len(hive.updates) == 1
    assert len(mycelium.broadcasts) == 1
    assert len(mycelium.propagations) == 1


def test_missing_composition_blocks_margin_close_and_is_felt_once() -> None:
    trader, raw, *_ = _wired_trader()

    result = trader.client.close_margin_position(
        symbol="XBTGBP",
        side="sell",
        volume=1,
        leverage=2,
    )

    assert result["decision"] == "HOLD"
    assert raw.mutation_calls == 0
    sensations = trader.recent_economic_sensations()
    assert [item["operation"] for item in sensations] == ["close_margin_position"]
    assert sensations[0]["actionable"] is False
    assert sensations[0]["eligible_for_learning"] is False


def test_unsupported_mycelium_is_not_reported_as_delivered() -> None:
    router = OrganismEconomicSensationRouter(mycelium_getter=lambda: object())

    observed = router.observe(
        "close_margin_position",
        {"status": "HOLD", "reason": "governance_required"},
    )

    assert observed["delivery"]["mycelium"] is False


def test_constructor_replaces_mutation_surface_after_existing_organs() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    constructor = source[
        source.index("class KrakenMarginArmyTrader:") : source.index(
            "    def _install_unity_exchange_brain"
        )
    ]
    installer = source[
        source.index("    def _install_unity_exchange_brain") : source.index(
            "    def recent_economic_sensations"
        )
    ]

    assert "unity_composition: Any = None" in constructor
    assert "trusted_unity_plan_supplier_ids" in constructor
    assert constructor.index("self.hive_state =") < constructor.index(
        "self._install_unity_exchange_brain("
    )
    assert "OrganismEconomicSensationRouter" in installer
    assert "build_queen_exchange_brains" in installer
    assert "outcome_observer=self._economic_sensation_router.observe" in installer
    assert 'self.client = brains["kraken"]' in installer
    assert source.count("self.client.place_margin_order(") == 1
    assert source.count("self.client.close_margin_position(") == 1
    assert "def recent_economic_sensations" in source
