import json
import math

import pytest

from aureon.autonomous.aureon_full_autonomous import QueenFullAutonomous


NOW = 2_000_000_000.0
SYMBOL = "BTCUSD"


class RecordingBus:
    def __init__(self):
        self.messages = []

    def think(self, payload, *, topic):
        self.messages.append((topic, json.loads(payload)))


class ReceiptValidator:
    def __init__(self, validator, score, source_timestamp, received_at):
        self.validator = validator
        self.score = score
        self.source_timestamp = source_timestamp
        self.received_at = received_at
        self.calls = []

    def _receipt(self, argument):
        self.calls.append(argument)
        return {
            "data_status": "real",
            "truth_status": "real_derived",
            "generated_values": False,
            "receipt_type": "validator_score",
            "receipt_id": f"validator:{self.validator}:1",
            "source_id": f"offline:{self.validator}",
            "source_timestamp": self.source_timestamp,
            "received_at": self.received_at,
            "freshness_ttl_sec": 30.0,
            "symbol": SYMBOL,
            "validator": self.validator,
            "score": self.score,
            "input_receipt_ids": ["market:1", "hnc:1", "auris:1"],
            "eligible_for_action": True,
            "eligible_for_accounting": False,
            "eligible_for_learning": True,
        }

    def validate(self, argument):
        return self._receipt(argument)

    def get_consensus(self, argument):
        return self._receipt(argument)

    def validate_opportunity(self, argument):
        return self._receipt(argument)


def _opportunity():
    observed = {
        "data_status": "real",
        "truth_status": "real_observed",
        "generated_values": False,
        "receipt_type": "market_opportunity",
        "receipt_id": "market:1",
        "source_id": "offline:market",
        "source_timestamp": NOW - 5.0,
        "received_at": NOW - 4.5,
        "freshness_ttl_sec": 30.0,
        "input_receipt_ids": [],
        "symbol": SYMBOL,
        "drift": 0.2,
        "eligible_for_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": True,
    }
    observed["hnc_receipt"] = {
        "data_status": "real",
        "truth_status": "real_derived",
        "generated_values": False,
        "receipt_type": "hnc_coherence",
        "receipt_id": "hnc:1",
        "source_id": "offline:hnc",
        "source_timestamp": NOW - 4.0,
        "received_at": NOW - 3.5,
        "freshness_ttl_sec": 30.0,
        "input_receipt_ids": ["market:1"],
        "symbol": SYMBOL,
        "gate_open": True,
        "eligible_for_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": True,
    }
    observed["auris_receipt"] = {
        "data_status": "real",
        "truth_status": "real_derived",
        "generated_values": False,
        "receipt_type": "auris_coherence",
        "receipt_id": "auris:1",
        "source_id": "offline:auris",
        "source_timestamp": NOW - 3.0,
        "received_at": NOW - 2.5,
        "freshness_ttl_sec": 30.0,
        "input_receipt_ids": ["market:1", "hnc:1"],
        "symbol": SYMBOL,
        "gate_open": True,
        "hnc_receipt_id": "hnc:1",
        "eligible_for_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": True,
    }
    return {"source": "scanner", "data": observed, "timestamp": NOW - 1.0}


def _controller(opportunity):
    controller = object.__new__(QueenFullAutonomous)
    controller._intel_state = {"opportunities": [opportunity]}
    controller._thought_bus = RecordingBus()
    controller._miner_brain = ReceiptValidator(
        "miner_brain", 0.9, NOW - 2.0, NOW - 1.5
    )
    controller._mycelium = ReceiptValidator(
        "mycelium", 0.8, NOW - 1.9, NOW - 1.4
    )
    controller._intelligence_engine = ReceiptValidator(
        "intelligence_engine", 0.85, NOW - 1.8, NOW - 1.3
    )
    return controller


def _contains_number(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, dict):
        return any(_contains_number(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_number(item) for item in value)
    return False


def test_missing_hnc_is_numeric_free_and_has_no_side_effects():
    opportunity = _opportunity()
    opportunity["data"].pop("hnc_receipt")
    controller = _controller(opportunity)

    result = controller._build_validation_result(opportunity, now=NOW)
    controller._run_validation_cycle(now=NOW)

    assert result["data_status"] == "no_data"
    assert not _contains_number(result)
    assert controller._thought_bus.messages == []
    assert controller._miner_brain.calls == []
    assert controller._mycelium.calls == []
    assert controller._intelligence_engine.calls == []


def test_stale_hnc_closes_gate_before_validators_or_publication():
    opportunity = _opportunity()
    opportunity["data"]["hnc_receipt"]["source_timestamp"] = NOW - 31.0
    controller = _controller(opportunity)

    result = controller._build_validation_result(opportunity, now=NOW)
    controller._run_validation_cycle(now=NOW)

    assert result["data_status"] == "no_data"
    assert not _contains_number(result)
    assert controller._thought_bus.messages == []
    assert controller._miner_brain.calls == []
    assert controller._mycelium.calls == []
    assert controller._intelligence_engine.calls == []


def test_complete_linked_chain_preserves_batten_equations_and_publishes_once():
    opportunity = _opportunity()
    controller = _controller(opportunity)

    controller._run_validation_cycle(now=NOW)

    assert len(controller._thought_bus.messages) == 1
    topic, result = controller._thought_bus.messages[0]
    assert topic == "validation.complete"
    assert result["data_status"] == "real"
    assert result["truth_status"] == "real_derived"
    assert result["passes"] == [0.9, 0.8, 0.85]
    assert result["coherence"] == pytest.approx(1 - (0.9 - 0.8))
    assert result["lambda"] == pytest.approx(math.exp(-0.5 * 0.2))
    assert result["4th_ready"] is True
    assert result["eligible_for_action"] is True
    assert result["generated_values"] is False
    assert result["input_receipt_ids"] == [
        "market:1",
        "hnc:1",
        "auris:1",
        "validator:miner_brain:1",
        "validator:mycelium:1",
        "validator:intelligence_engine:1",
    ]
    assert result["receipt_id"].startswith("full-autonomous-validation:")
    assert len(controller._miner_brain.calls) == 1
    assert len(controller._mycelium.calls) == 1
    assert len(controller._intelligence_engine.calls) == 1
