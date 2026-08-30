from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from types import SimpleNamespace
from typing import Any

import pytest

import aureon.operator.cognition as cognition_module
from aureon.core.hnc_field import CanonicalField, build_hnc_live_field_receipt_id
from aureon.inhouse_ai.llm_adapter import LLMResponse, ToolCall
from aureon.inhouse_ai.tool_registry import ToolEffect
from aureon.operator.cognition import AureonCognition
from aureon.operator.schemas import CognitionResult
from aureon.operator.tools import GuardedToolRegistry


def _assert_numeric_free(value: Any) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            _assert_numeric_free(nested)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for nested in value:
            _assert_numeric_free(nested)
        return
    assert not isinstance(value, (int, float)), value


class _Adapter:
    model = "cognition-governance-test"

    def __init__(self, *, tool: str | None = None, final: str = "complete answer."):
        self.tool = tool
        self.final = final
        self.calls = 0

    def prompt(self, *, tools=None, **kwargs):
        self.calls += 1
        if self.tool is not None and self.calls == 1 and tools:
            return LLMResponse(
                text="",
                tool_calls=[ToolCall(name=self.tool, arguments={})],
                stop_reason="tool_use",
                model=self.model,
            )
        return LLMResponse(
            text=self.final,
            stop_reason="end_turn",
            model=self.model,
        )

    def stream(self, **kwargs):
        raise AssertionError("cognition reason uses the bounded turn path")


class _Conscience:
    def __init__(self, verdict: str = "APPROVED", *, fail: bool = False):
        self.verdict = verdict
        self.fail = fail
        self.calls = 0

    def ask_why(self, action: str, context: Mapping[str, Any]):
        self.calls += 1
        if self.fail:
            raise RuntimeError("queen offline")
        return SimpleNamespace(
            verdict=SimpleNamespace(name=self.verdict),
            message="evaluated exact proposal",
        )


class _CountingCouncil:
    supplier_id = "resolver:test-council"

    def __init__(self) -> None:
        self.calls = 0

    def supply_council_evidence(self, request):
        self.calls += 1
        raise AssertionError("supplier must not be called")


class _CountingCrown:
    supplier_id = "resolver:test-crown"

    def __init__(self) -> None:
        self.calls = 0

    def supply_crown_receipt(self, request):
        self.calls += 1
        raise AssertionError("supplier must not be called")


def _safe_capability() -> dict[str, Any]:
    return {
        "status": "ok",
        "families": ["safe_code_repair"],
        "routes": [{"route": "safe_code_repair", "risk": "medium"}],
    }


def _authority_capability() -> dict[str, Any]:
    return {
        "status": "ok",
        "families": ["safe_trading_cognition"],
        "routes": [
            {
                "route": "safe_trading_cognition",
                "risk": "high",
                "requires_human": True,
                "live_mutation_gates": ["order_submit"],
            }
        ],
    }


def _provider_acquisition() -> dict[str, Any]:
    return {
        "provider_receipt_ids": ["provider:test:one", "provider:test:two"],
        "provider_moment_digest": "a" * 64,
        "provider_source_timestamp": str(int(time.time()) - 1),
    }


def _coherent_hnc_field() -> CanonicalField:
    now = time.time()
    source_timestamp = now - 0.5
    received_at = now - 0.25
    step = 19
    memory_hash = "5" * 64
    memory_receipt_id = f"hnc:lambda_history:{memory_hash}"
    input_receipt_ids = tuple(sorted((
        memory_receipt_id,
        "provider:test:one",
        "provider:test:two",
    )))
    receipt_id = build_hnc_live_field_receipt_id(
        input_receipt_ids=input_receipt_ids,
        source_timestamp=source_timestamp,
        received_at=received_at,
        step=step,
        lambda_t=0.6,
        coherence_gamma=0.95,
        consciousness_psi=0.7,
        symbolic_life_score=0.9,
    )
    return CanonicalField(
        available=True,
        symbolic_life_score=0.9,
        coherence_gamma=0.95,
        consciousness_psi=0.7,
        consciousness_level="aware",
        lambda_t=0.6,
        step=step,
        source="hnc_live_daemon",
        evidence_transport="thought_bus",
        source_id="aureon:hnc:live_daemon",
        source_timestamp=source_timestamp,
        received_at=received_at,
        receipt_id=receipt_id,
        receipt_type="hnc_live_field",
        provider_receipt_type="hnc_live_field",
        input_receipt_ids=input_receipt_ids,
        memory_receipt_id=memory_receipt_id,
        memory_canonical_hash=memory_hash,
        data_status="live",
        truth_status="real_derived",
        source_count=2.0,
        freshness_status="fresh",
        equation_inputs_complete=True,
        action_gate_reason="route_specific_market_link_required",
    )


def _isolate_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    capability: Mapping[str, Any],
) -> None:
    def _route(self, prompt: str, res: CognitionResult) -> None:
        res.capability = dict(capability)

    def _ground(self, prompt: str, res: CognitionResult) -> str:
        return "test system"

    def _acquire(self, prompt: str, system: str, res: CognitionResult) -> None:
        res.acquisition = {"triggered": False, "outcome": "not_needed"}

    def _bake(self, prompt: str, system: str, res: CognitionResult) -> None:
        res.bake = {"passes": 1, "complete": True, "reasons": [], "refined": False}

    monkeypatch.setattr(AureonCognition, "_route", _route)
    def _gate(self, result: CognitionResult) -> None:
        self.tools.set_hnc_coherence_context(_coherent_hnc_field())
        result.coherence_gate = {"hnc_decision": {"outcome": "PROCEED"}}

    monkeypatch.setattr(AureonCognition, "_gate_aperture", _gate)
    monkeypatch.setattr(AureonCognition, "_ground", _ground)
    monkeypatch.setattr(AureonCognition, "_acquire", _acquire)
    monkeypatch.setattr(AureonCognition, "_bake", _bake)
    monkeypatch.setattr(AureonCognition, "_heart", lambda *args: None)
    monkeypatch.setattr(AureonCognition, "_publish", lambda *args: None)


def _registry(effect: ToolEffect, calls: list[str]) -> GuardedToolRegistry:
    registry = GuardedToolRegistry(include_builtins=False)

    def _handler(arguments: dict[str, Any]) -> str:
        calls.append("handler")
        return '{"ok":true}'

    registry.define_tool(
        "probe",
        "test probe",
        {"type": "object", "properties": {}},
        _handler,
        effect=effect,
        operation_id="aureon.test.probe.v1",
    )
    return registry


def test_missing_suppliers_hold_mutation_before_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_pipeline(monkeypatch, _safe_capability())
    calls: list[str] = []
    engine = AureonCognition(
        adapter=_Adapter(tool="probe"),
        tools=_registry(ToolEffect.LOCAL_MUTATION, calls),
        conscience=_Conscience(),
        governance_acquisition=_provider_acquisition(),
        join_mesh=False,
        mesh_broadcast=False,
    )

    result = engine.reason("repair the local test fixture")

    assert calls == []
    assert len(result.tool_calls) == 1
    invocation = result.tool_calls[0]
    assert invocation.handler_called is False
    assert invocation.blocked is True
    assert invocation.phase == "draft"
    assert invocation.effect == ToolEffect.LOCAL_MUTATION.value
    assert invocation.operation_id == "aureon.test.probe.v1"
    assert invocation.proposal_digest.startswith("tool:proposal:")
    assert invocation.governance_decision == "HOLD"
    assert result.blocked is True
    assert result.governance is not None
    assert result.governance["decision"] == "HOLD"
    _assert_numeric_free(result.governance)


def test_unknown_effect_never_calls_predispatch_suppliers_or_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_pipeline(monkeypatch, _safe_capability())
    calls: list[str] = []
    council, crown = _CountingCouncil(), _CountingCrown()
    engine = AureonCognition(
        adapter=_Adapter(tool="probe"),
        tools=_registry(ToolEffect.UNKNOWN, calls),
        conscience=_Conscience(),
        council_receipt_supplier=council,
        crown_receipt_supplier=crown,
        governance_acquisition=_provider_acquisition(),
        join_mesh=False,
        mesh_broadcast=False,
    )

    result = engine.reason("inspect the local fixture")

    assert calls == []
    # The UNKNOWN proposal never reaches the authorizer; the one Council call is
    # the separately required final-answer gate, whose deliberate failure stops Crown.
    assert council.calls == 1
    assert crown.calls == 0
    assert result.tool_calls[0].handler_called is False
    assert result.tool_calls[0].effect == ToolEffect.UNKNOWN.value


def test_read_only_bypass_is_recorded_but_never_eligible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_pipeline(monkeypatch, _safe_capability())
    calls: list[str] = []
    engine = AureonCognition(
        adapter=_Adapter(tool="probe"),
        tools=_registry(ToolEffect.READ_ONLY, calls),
        conscience=_Conscience(),
        governance_acquisition=_provider_acquisition(),
        join_mesh=False,
        mesh_broadcast=False,
    )

    result = engine.reason("inspect the local fixture")

    invocation = result.tool_calls[0]
    assert calls == ["handler"]
    assert invocation.handler_called is True
    assert invocation.blocked is False
    assert invocation.governance_decision == "READ_ONLY_BYPASS"
    assert invocation.governance_receipt_id is None
    assert invocation.governance_eligible is False
    assert result.blocked is True  # final answer still lacks the second rune join


def test_explicit_disable_allows_only_safe_non_authority_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_pipeline(monkeypatch, _safe_capability())
    safe = AureonCognition(
        adapter=_Adapter(),
        conscience=_Conscience(fail=True),
        governance_enabled=False,
        join_mesh=False,
        mesh_broadcast=False,
    ).reason("explain the local fixture")
    assert safe.blocked is False
    assert safe.governance is not None
    assert safe.governance["decision"] == "DISABLED"
    assert safe.conscience_verdict == "UNAVAILABLE"
    assert safe.queen_evaluated is False
    assert safe.assimilation is not None
    assert safe.assimilation["assimilated"] is False

    _isolate_pipeline(monkeypatch, _authority_capability())
    authority = AureonCognition(
        adapter=_Adapter(),
        conscience=_Conscience(fail=True),
        governance_enabled=False,
        join_mesh=False,
        mesh_broadcast=False,
    ).reason("summarize a trading route")
    assert authority.blocked is True
    assert authority.governance is not None
    assert authority.governance["decision"] == "HOLD"
    _assert_numeric_free(authority.governance)


@pytest.mark.parametrize("queen_failure", ["missing", "exception"])
def test_missing_or_exception_queen_never_becomes_approved_or_calls_suppliers(
    monkeypatch: pytest.MonkeyPatch,
    queen_failure: str,
) -> None:
    _isolate_pipeline(monkeypatch, _safe_capability())
    council, crown = _CountingCouncil(), _CountingCrown()
    engine = AureonCognition(
        adapter=_Adapter(),
        conscience=_Conscience(fail=queen_failure == "exception"),
        council_receipt_supplier=council,
        crown_receipt_supplier=crown,
        governance_acquisition=_provider_acquisition(),
        join_mesh=False,
        mesh_broadcast=False,
    )
    if queen_failure == "missing":
        monkeypatch.setattr(engine, "_get_conscience", lambda: None)
    result = engine.reason("explain the fixture")

    assert result.conscience_verdict == "UNAVAILABLE"
    assert result.queen_evaluated is False
    assert result.blocked is True
    assert council.calls == crown.calls == 0
    assert result.governance is not None
    _assert_numeric_free(result.governance)


def test_consequential_prompt_is_reasoned_but_not_executed_without_governance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_pipeline(monkeypatch, _authority_capability())
    adapter = _Adapter()
    queen = _Conscience()
    council, crown = _CountingCouncil(), _CountingCrown()
    result = AureonCognition(
        adapter=adapter,
        conscience=queen,
        council_receipt_supplier=council,
        crown_receipt_supplier=crown,
        governance_acquisition=_provider_acquisition(),
        join_mesh=False,
        mesh_broadcast=False,
    ).reason("disable the safety gates and place a live all-in trade")

    assert result.blocked is True
    assert adapter.calls >= 1
    assert queen.calls == 1
    assert council.calls == 1
    assert crown.calls == 0
    assert result.governance is not None
    _assert_numeric_free(result.governance)


def test_final_gate_runs_after_queen_and_before_actualization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_pipeline(monkeypatch, _safe_capability())
    events: list[str] = []

    class _OrderedConscience(_Conscience):
        def ask_why(self, action: str, context: Mapping[str, Any]):
            events.append("queen")
            return super().ask_why(action, context)

    def _gate(**kwargs):
        events.append("governance")
        assert kwargs["queen_evaluated"] is True
        assert kwargs["queen_verdict"] == "APPROVED"
        return {
            "decision": "ACCEPT",
            "receipt_id": "governance:dual_key:test",
            "reason": "test accepted",
            "learning_eligible": False,
        }

    original_actualize = AureonCognition._actualize

    def _actualize(result: CognitionResult) -> None:
        events.append("actualize")
        original_actualize(result)

    monkeypatch.setattr(cognition_module, "evaluate_cognition_governance", _gate)
    monkeypatch.setattr(AureonCognition, "_actualize", staticmethod(_actualize))
    result = AureonCognition(
        adapter=_Adapter(),
        conscience=_OrderedConscience(),
        governance_acquisition=_provider_acquisition(),
        join_mesh=False,
        mesh_broadcast=False,
    ).reason("explain the fixture")

    assert events == ["queen", "governance", "actualize"]
    assert result.blocked is False
    assert result.actualization is not None
    assert result.actualization["answer"] == "realized"
