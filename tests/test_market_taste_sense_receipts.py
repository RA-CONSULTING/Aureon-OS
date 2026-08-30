from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from aureon.intelligence.aureon_market_taste_sense import MarketTasteSense


TARGET = (
    Path(__file__).resolve().parents[1]
    / "aureon"
    / "intelligence"
    / "aureon_market_taste_sense.py"
)


class _Sequencer:
    def __init__(self) -> None:
        self.last_molecule = None

    def sequence(self, molecule):
        self.last_molecule = molecule
        return SimpleNamespace(
            taste_score=0.70,
            sweetness_norm=0.80,
            binding_norm=0.40,
        )

    @staticmethod
    def map_to_frequency(_properties):
        return 528.0, "Love", "green"


def _evidence(*, now: float = 1_000.0, gate_open: bool = True) -> dict:
    market = {
        "receipt_type": "market_snapshot",
        "receipt_id": "market-1",
        "source_id": "kraken:ohlcv",
        "venue": "kraken",
        "symbol": "BTC/USD",
        "timeframe": "24h",
        "source_timestamp": now - 10.0,
        "received_at": now - 9.0,
        "truth_status": "real_observed",
        "generated_values": False,
        "eligible_for_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": True,
        "price_change_24h_pct": 5.2,
        "price_change_7d_pct": 12.4,
        "trend_persistence": 4,
        "n_correlated_moving": 12,
        "n_anomaly_events": 1,
        "asset_weight": 520.0,
    }
    hnc = {
        "receipt_type": "hnc_coherence",
        "receipt_id": "hnc-1",
        "source_id": "hnc:canonical",
        "venue": "kraken",
        "symbol": "BTC/USD",
        "timeframe": "24h",
        "source_timestamp": now - 8.0,
        "received_at": now - 7.0,
        "truth_status": "real_derived",
        "generated_values": False,
        "eligible_for_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": True,
        "input_receipt_ids": ["market-1"],
        "coherence": 0.80,
        "gate_open": gate_open,
    }
    auris = {
        "receipt_type": "auris_coherence",
        "receipt_id": "auris-1",
        "source_id": "auris:canonical",
        "venue": "kraken",
        "symbol": "BTC/USD",
        "timeframe": "24h",
        "source_timestamp": now - 6.0,
        "received_at": now - 5.0,
        "truth_status": "real_derived",
        "generated_values": False,
        "eligible_for_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": True,
        "input_receipt_ids": ["market-1", "hnc-1"],
        "coherence": 0.90,
        "gate_open": gate_open,
    }
    return {
        "market_receipt": market,
        "hnc_receipt": hnc,
        "auris_receipt": auris,
    }


def _numeric_values(value):
    if isinstance(value, dict):
        for nested in value.values():
            yield from _numeric_values(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            yield from _numeric_values(nested)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield value


def test_market_taste_requires_linked_fresh_receipts_and_mutates_once() -> None:
    source = TARGET.read_text(encoding="utf-8")
    assert "_baton_link" not in source
    assert 'if __name__ == "__main__"' not in source
    assert "ASSET_WEIGHT_TABLE" not in source

    raw_engine = MarketTasteSense(sequencer=_Sequencer(), clock=lambda: 1_000.0)
    no_data = raw_engine.taste_market(
        "BTC/USD",
        {"price_change_24h_pct": 5.2},
        "24h",
    )
    assert no_data["status"] == "no_data"
    assert no_data["eligible_for_action"] is False
    assert no_data["eligible_for_accounting"] is False
    assert no_data["eligible_for_learning"] is False
    assert list(_numeric_values(no_data)) == []
    assert raw_engine._profiles == {}

    stale = _evidence()
    for receipt in stale.values():
        receipt["source_timestamp"] -= 500.0
        receipt["received_at"] -= 500.0
    stale_result = raw_engine.taste_market("BTC/USD", stale, "24h")
    assert stale_result["status"] == "no_data"
    assert raw_engine._profiles == {}

    sequencer = _Sequencer()
    engine = MarketTasteSense(sequencer=sequencer, clock=lambda: 1_000.0)
    evidence = _evidence()
    profile = engine.taste_market("BTC/USD", evidence, "24h")

    assert profile.symbol == "BTCUSD"
    assert profile.venue == "kraken"
    assert profile.source_timestamp == 990.0
    assert profile.received_at == 995.0
    assert profile.input_receipt_ids == ("market-1", "hnc-1", "auris-1")
    assert profile.truth_status == "real_derived"
    assert profile.generated_values is False
    assert profile.eligible_for_action is True
    assert profile.eligible_for_accounting is False
    assert profile.eligible_for_learning is True
    assert profile.too_much_index == 0.1567
    assert profile.turning_point_score == 0.0135
    assert profile.hnc_coherence == 0.80
    assert profile.auris_coherence == 0.90
    assert profile.taste_experience.brain_input is None
    assert profile.taste_experience.source_timestamp == 990.0
    assert profile.taste_experience.sequenced_at == 994.0
    assert sequencer.last_molecule.molecular_weight == 520.0
    assert len(engine._profiles["BTCUSD"]) == 1

    replay = engine.taste_market("BTC/USD", deepcopy(evidence), "24h")
    assert replay["status"] == "no_data"
    assert replay["reason"] == "receipt_replay_rejected"
    assert len(engine._profiles["BTCUSD"]) == 1


def test_closed_coherence_gates_remain_observational_and_nonlearning() -> None:
    engine = MarketTasteSense(sequencer=_Sequencer(), clock=lambda: 1_000.0)
    profile = engine.taste_market("BTC/USD", _evidence(gate_open=False), "24h")

    assert profile.action_hint == "observe_only"
    assert profile.eligible_for_action is False
    assert profile.eligible_for_accounting is False
    assert profile.eligible_for_learning is False
    assert profile.taste_experience.brain_input is None
    assert engine._profiles == {}
    no_history = engine.detect_sweet_to_sour("BTC/USD")
    assert no_history["status"] == "no_data"
    assert list(_numeric_values(no_history)) == []
