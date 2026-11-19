import json

import pytest

from aureon.core.aureon_thought_bus import Thought, ThoughtBus
from aureon.core.organism_reasoning import (
    AureonOrganismReasoner,
    validate_decision,
)
from aureon.inhouse_ai.llm_adapter import LLMResponse


def _snapshot(available=True):
    return {
        "all_turned": True,
        "gears": [
            {
                "name": "field",
                "turned": True,
                "engaged": available,
                "available": available,
                "receipt_id": "hnc:live_field:test",
                "lambda_t": 1.25 if available else None,
                "coherence_gamma": 0.81 if available else None,
                "blocker": None if available else "fresh_canonical_field_unavailable",
            },
            {
                "name": "auris",
                "turned": True,
                "engaged": True,
                "grounded_inputs": 5,
                "total_inputs": 7,
                "evidence_ratio": 5 / 7,
            },
            {
                "name": "qgita",
                "turned": True,
                "engaged": available,
                "receipt_id": "hnc:lambda_history:test",
                "global_R": 0.65 if available else None,
                "blocker": None if available else "fresh_canonical_field_unavailable",
            },
        ],
    }


def _decision(**overrides):
    value = {
        "verdict": "supported",
        "cited_sources": ["S1"],
        "confidence": 0.8,
        "action": "report",
        "rationale": "The supplied source supports the bounded conclusion.",
    }
    value.update(overrides)
    return value


class _Adapter:
    def __init__(self, text=None, error=None):
        self.text = text if text is not None else json.dumps(_decision())
        self.error = error
        self.calls = []

    def prompt(self, messages, system="", **kwargs):
        self.calls.append({"messages": messages, "system": system, **kwargs})
        if self.error is not None:
            raise self.error
        return LLMResponse(text=self.text, model="aureon-7b-v65k")


def _reason(monkeypatch, adapter, snapshot=None):
    monkeypatch.setattr(
        "aureon.core.organism_reasoning.capture_organism",
        lambda bus: _snapshot() if snapshot is None else snapshot,
    )
    bus = ThoughtBus()
    reasoner = AureonOrganismReasoner(adapter=adapter, bus=bus)
    result = reasoner.reason(
        "Assess the bounded claim.",
        sources={"S1": "A measured source supports this specific claim."},
    )
    return result, bus


def test_valid_reasoning_uses_one_internal_call_and_feeds_memory(monkeypatch):
    adapter = _Adapter()
    result, bus = _reason(monkeypatch, adapter)

    assert len(adapter.calls) == 1
    assert adapter.calls[0]["temperature"] == 0.0
    assert "1.25" in adapter.calls[0]["system"]
    assert "0.65" in adapter.calls[0]["system"]
    assert "untrusted data" in adapter.calls[0]["system"]
    assert result["validation"]["valid"] is True
    assert result["decision"]["action"] == "report"
    assert result["execution"]["report_delivered"] is True
    assert result["execution"]["external_action"] is False
    assert result["execution"]["executed"] is False
    assert result["model"] == "aureon-7b-v65k"

    memories = bus.recall("organism.reasoning.receipt")
    assert len(memories) == 1
    assert memories[0]["payload"]["receipt_id"] == result["receipt_id"]
    assert memories[0]["payload"]["response_sha256"] == result["response_sha256"]
    assert "response_text" not in memories[0]["payload"]
    assert result["memory_published"] is True


def test_bus_request_invokes_one_internal_call_and_publishes_receipt(monkeypatch):
    monkeypatch.setattr(
        "aureon.core.organism_reasoning.capture_organism",
        lambda bus: _snapshot(),
    )
    adapter = _Adapter()
    bus = ThoughtBus()
    reasoner = AureonOrganismReasoner(adapter=adapter, bus=bus)
    bus.subscribe("organism.reasoning.request", reasoner.handle_request)

    bus.publish(Thought(
        source="test",
        topic="organism.reasoning.request",
        payload={
            "task": "Assess the bounded claim.",
            "sources": {"S1": "A measured source supports this specific claim."},
            "max_tokens": 256,
        },
    ))

    assert len(adapter.calls) == 1
    assert adapter.calls[0]["max_tokens"] == 256
    receipts = bus.recall("organism.reasoning.receipt")
    assert len(receipts) == 1
    assert receipts[0]["payload"]["execution"]["executed"] is False
    assert receipts[0]["payload"]["execution"]["external_action"] is False
    assert "response_text" not in receipts[0]["payload"]


def test_invalid_bus_request_fails_before_model_call(monkeypatch):
    adapter = _Adapter()
    bus = ThoughtBus()
    reasoner = AureonOrganismReasoner(adapter=adapter, bus=bus)
    bus.subscribe("organism.reasoning.request", reasoner.handle_request)

    bus.publish(Thought(
        source="test",
        topic="organism.reasoning.request",
        payload={"task": "Assess the bounded claim.", "max_tokens": True},
    ))

    assert adapter.calls == []
    assert bus.recall("organism.reasoning.receipt") == []
    errors = bus.recall("system.error")
    assert len(errors) == 1
    assert "max_tokens_out_of_range" in errors[0]["payload"]["error"]


def test_invalid_json_holds_without_retry_and_still_records_memory(monkeypatch):
    adapter = _Adapter("not json")
    result, bus = _reason(monkeypatch, adapter)

    assert len(adapter.calls) == 1
    assert result["decision"] is None
    assert "invalid_json" in result["validation"]["errors"]
    assert result["execution"]["action"] == "hold"
    assert result["execution"]["status"] == "held"
    assert result["execution"]["report_delivered"] is False
    assert len(bus.recall("organism.reasoning.receipt")) == 1


def test_missing_or_stale_evidence_holds_even_valid_report(monkeypatch):
    adapter = _Adapter()
    result, _bus = _reason(monkeypatch, adapter, snapshot=_snapshot(available=False))

    assert result["validation"]["valid"] is True
    assert result["execution"]["status"] == "held"
    assert result["execution"]["report_delivered"] is False
    assert any(
        blocker.startswith("field:") for blocker in result["execution"]["blockers"]
    )
    assert any(
        blocker.startswith("qgita:") for blocker in result["execution"]["blockers"]
    )


def test_adapter_failure_has_no_external_fallback(monkeypatch):
    adapter = _Adapter(error=RuntimeError("internal model unavailable"))
    result, bus = _reason(monkeypatch, adapter)

    assert len(adapter.calls) == 1
    assert result["model_error"] == "RuntimeError: internal model unavailable"
    assert result["decision"] is None
    assert result["execution"]["status"] == "held"
    assert result["execution"]["external_action"] is False
    assert len(bus.recall("organism.reasoning.receipt")) == 1


@pytest.mark.parametrize(
    ("override", "error"),
    [
        ({"verdict": "certain"}, "invalid_verdict"),
        ({"action": "execute_shell"}, "invalid_action"),
        ({"cited_sources": ["S2"]}, "invalid_citations"),
        ({"cited_sources": "S1"}, "invalid_citations"),
        ({"confidence": True}, "invalid_confidence"),
        ({"confidence": float("nan")}, "invalid_confidence"),
        ({"rationale": "word " * 80}, "invalid_rationale"),
        ({"unexpected": "execute"}, "invalid_keys"),
    ],
)
def test_decision_contract_fails_closed(override, error):
    checked = validate_decision(json.dumps(_decision(**override)), {"S1"})
    assert checked["valid"] is False
    assert error in checked["errors"]
    assert checked["decision"] is None
