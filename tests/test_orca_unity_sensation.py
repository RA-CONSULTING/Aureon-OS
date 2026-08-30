from __future__ import annotations

from pathlib import Path
from typing import Any

from aureon.core.economic_sensation import (
    OrganismEconomicSensationRouter,
    economic_sensation,
)
from aureon.queen.unity_exchange_brain import build_queen_exchange_brains

ROOT = Path(__file__).resolve().parents[1]
ORCA_SOURCE = ROOT / "aureon" / "bots" / "orca_complete_kill_cycle.py"


class _Bus:
    def __init__(self) -> None:
        self.thoughts: list[Any] = []

    def publish(self, thought: Any) -> None:
        self.thoughts.append(thought)


class _Hive:
    def __init__(self) -> None:
        self.updates: list[dict[str, Any]] = []
        self.messages: list[str] = []

    def update(self, **kwargs: Any) -> None:
        self.updates.append(kwargs)

    def log_message(self, message: str) -> None:
        self.messages.append(message)


class _Mycelium:
    def __init__(self) -> None:
        self.broadcasts: list[tuple[str, dict[str, Any]]] = []
        self.propagations: list[tuple[str, dict[str, Any]]] = []

    def broadcast_signal(self, name: str, payload: dict[str, Any]) -> None:
        self.broadcasts.append((name, payload))

    def propagate_to_all(self, name: str, payload: dict[str, Any]) -> int:
        self.propagations.append((name, payload))
        return 1


class _ReadClient:
    dry_run = False

    def __init__(self) -> None:
        self.order_calls = 0

    def get_ticker(self, symbol: str) -> dict[str, Any]:
        return {"symbol": symbol, "price": 1.0}

    def place_market_order(self, *args: Any, **kwargs: Any) -> None:
        self.order_calls += 1


def test_hold_is_feedback_only_protective_machine_state() -> None:
    result = economic_sensation(
        "place_market_order",
        {
            "status": "no_data",
            "decision": "HOLD",
            "reason": "canonical_queen_unity_composition_required",
            "exchange": "kraken",
            "symbol": "XBTGBP",
            "truth_status": "no_data",
        },
    )

    assert result["felt_state"] == "PROTECTIVE_HOLD"
    assert result["executed"] is False
    assert result["feedback_only"] is True
    assert result["actionable"] is False
    assert result["action_eligible"] is False
    assert result["economic_mutation"] is False
    assert result["eligible_for_accounting"] is False
    assert result["eligible_for_learning"] is False
    assert result["not_human_sensation"] is True


def test_nested_executed_receipt_is_resolved_without_granting_authority() -> None:
    result = economic_sensation(
        "place_market_order",
        {
            "status": "submitted",
            "symbol": "XBTGBP",
            "aureon_legacy_unity_receipt": {
                "status": "EXECUTED",
                "venue": "kraken",
                "symbol": "XBTGBP",
                "receipt_id": "legacy-unity:receipt:1",
                "truth_status": "real_observed",
            },
        },
    )

    assert result["status"] == "EXECUTED"
    assert result["felt_state"] == "RESOLVED_EXECUTION"
    assert result["executed"] is True
    assert result["receipt_id"] == "legacy-unity:receipt:1"
    assert result["actionable"] is False


def test_router_fans_one_sensation_to_bus_hive_and_mycelium() -> None:
    bus = _Bus()
    hive = _Hive()
    mycelium = _Mycelium()
    router = OrganismEconomicSensationRouter(
        bus_getter=lambda: bus,
        hive_getter=lambda: hive,
        mycelium_getter=lambda: mycelium,
    )

    observed = router.observe(
        "place_market_order",
        {
            "status": "no_data",
            "reason": "exact_unified_ecosystem_plan_required",
            "exchange": "binance",
            "symbol": "BTCUSDT",
        },
    )

    assert observed["delivery"] == {
        "thought_bus": True,
        "hive": True,
        "mycelium": True,
    }
    assert len(bus.thoughts) == 1
    assert bus.thoughts[0].topic == "organism.economic.sensation"
    assert bus.thoughts[0].payload["felt_state"] == "PROTECTIVE_HOLD"
    assert hive.updates == [
        {
            "mood": "Protective",
            "scanner": "economic:binance:place_market_order",
            "veto_reason": "exact_unified_ecosystem_plan_required",
        }
    ]
    assert len(hive.messages) == 1
    assert mycelium.broadcasts[0][0] == "economic_sensation"
    assert mycelium.propagations[0][0] == "economic_sensation"
    assert router.recent() == [observed]


def test_sink_failure_never_changes_or_retries_the_outcome() -> None:
    calls = 0

    def broken_bus() -> Any:
        nonlocal calls
        calls += 1
        raise RuntimeError("sink unavailable")

    router = OrganismEconomicSensationRouter(bus_getter=broken_bus)
    observed = router.observe(
        "place_market_order",
        {"status": "not_submitted", "reason": "blocked"},
    )

    assert calls == 1
    assert observed["felt_state"] == "PROTECTIVE_HOLD"
    assert observed["delivery"]["thought_bus"] is False
    assert len(router.recent()) == 1


def test_missing_composition_is_observed_once_and_never_calls_raw_client() -> None:
    raw = _ReadClient()
    observed: list[tuple[str, dict[str, Any]]] = []
    brains, governed, _ = build_queen_exchange_brains(
        fallback_read_clients={"kraken": raw},
        outcome_observer=lambda operation, receipt: observed.append(
            (operation, dict(receipt))
        ),
    )

    result = brains["kraken"].place_market_order(
        "XBTGBP",
        "buy",
        quote_qty=10,
    )

    assert governed is None
    assert result["decision"] == "HOLD"
    assert raw.order_calls == 0
    assert observed == [("place_market_order", result)]


def test_margin_close_is_governed_and_observed_not_read_fallback() -> None:
    raw = _ReadClient()
    observed: list[tuple[str, dict[str, Any]]] = []
    brains, _, _ = build_queen_exchange_brains(
        fallback_read_clients={"kraken": raw},
        outcome_observer=lambda operation, receipt: observed.append(
            (operation, dict(receipt))
        ),
    )

    result = brains["kraken"].close_margin_position("XBTGBP", "sell", volume=1)

    assert result["decision"] == "HOLD"
    assert result["reason"] == "canonical_queen_unity_composition_required"
    assert raw.order_calls == 0
    assert observed == [("close_margin_position", result)]


def test_orca_installs_shared_brain_after_organs_and_exposes_history() -> None:
    source = ORCA_SOURCE.read_text(encoding="utf-8")
    constructor = source[source.index("class OrcaKillCycle:") : source.index("    def audit_event")]

    assert "unity_composition=None" in constructor
    assert "OrganismEconomicSensationRouter" in constructor
    assert "build_queen_exchange_brains" in constructor
    assert "outcome_observer=self.economic_sensation_router.observe" in constructor
    assert "self.clients = brains" in constructor
    assert constructor.index("self.mycelium_network = None") < constructor.index(
        "OrganismEconomicSensationRouter"
    )
    assert "def recent_economic_sensations" in source
    assert source.count("self._governed_client_for(") == 16
    assert "client.place_market_order" not in source
    assert "client.place_margin_order" not in source
    assert "pos.client.close_margin_position" not in source
    assert "pos.client.place_market_order" not in source


def test_orca_lazy_capital_client_cannot_replace_mutation_authority() -> None:
    source = ORCA_SOURCE.read_text(encoding="utf-8")
    method = source[source.index("    def _ensure_capital_client") : source.index("    def emit_position_signal")]

    assert "QueenGovernedExchangeBrain" in method
    assert "governed_client=self._governed_unity_client" in method
    assert "outcome_observer=self.economic_sensation_router.observe" in method
    assert "self.clients['capital'] = raw_client" not in method
